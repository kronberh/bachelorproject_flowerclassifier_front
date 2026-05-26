import os
import asyncio
import requests
import tempfile
from dotenv import load_dotenv
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram import Bot, Dispatcher, F, Router

from enums import AnswerCompleteness
from keyboards import learn_more_keyboard, probability_threshold_keyboard, settings_keyboard, answer_completeness_keyboard, privacy_keyboard

load_dotenv()

BOT_TOKEN = os.environ.get('BOT_TOKEN')
API_ENDPOINT = os.environ.get('API_ENDPOINT')
MODEL_ENDPOINT = os.environ.get('MODEL_ENDPOINT')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

MIN_PROBABILITY_THRESHOLD = 0
MAX_PROBABILITY_THRESHOLD = 50
MESSAGE_LENGTH_LIMIT = 4096
INLINE_BUTTONS_LIMIT = 100

# Command handlers
@dp.message(Command('start'))
async def command_start_handler(message: Message):
    await message.answer('Welcome to Flower Classifier Bot! Send me an image of a flower and I\'ll try to classify it!')

@dp.message(Command('settings'))
async def command_settings_handler(message: Message):
    await message.answer(
        'Which setting do you want to modify?',
        reply_markup=settings_keyboard()
    )

# Image handler
@dp.message(F.photo)
async def classify_photo(message: Message, bot: Bot):
    loading_msg = await message.answer('Loading...')
    
    response = requests.get(f'{API_ENDPOINT}/telegram-users/{message.from_user.id}/?format=json')
    if response.status_code == 200:
        data = response.json()

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
        image_path = tmp.name
    await bot.download_file(file.file_path, image_path)
    
    with open(image_path, 'rb') as f:
        response = requests.post(
            f'{MODEL_ENDPOINT}/classify',
            files={'file': f},
            params={'threshold': data['probability_threshold']}
        )
    if response.status_code != 200:
        await loading_msg.edit_text('Sorry, the model server is down. Please try again later.')
        os.remove(image_path)
        return
    
    results = response.json()
    flower_id, confidence = results[0]
    other_results = results[1:INLINE_BUTTONS_LIMIT]

    results_names = []

    response = requests.get(f'{API_ENDPOINT}/flowers/{flower_id + 1}/?format=json')
    if response.status_code == 200:
        flower_data = response.json()
        text = f'With a probability of <b>{(confidence * 100):.1f}%</b>, this is <b>{flower_data['name']}</b>'
        
        if data['answer_completeness'] == AnswerCompleteness.SHORT.value.id:
            text += f'\n<i>{flower_data['short_description']}</i>'
        elif data['answer_completeness'] == AnswerCompleteness.FULL.value.id:
            text += f'\n<i>{flower_data['long_description']}</i>'
        
        if len(other_results) > 0:
            text += '\n\nThis may also be:'
            for other_flower_id, other_conf in other_results:
                other_response = requests.get(f'{API_ENDPOINT}/flowers/{other_flower_id + 1}/?format=json')
                text_to_append = ''
                if other_response.status_code == 200:
                    other_flower_data = other_response.json()
                    text_to_append = f'\n- <i>{other_flower_data['name']}</i> ({(other_conf * 100):.1f}%);'
                    if (len(text) + len(text_to_append)) <= MESSAGE_LENGTH_LIMIT:
                        results_names.append({'id': other_flower_data['id'], 'name': other_flower_data['name']})
                else:
                    text_to_append = f'\n- <i>Unknown flower with id={other_flower_id + 1}</i> ({(other_conf * 100):.1f}%);'
                if (len(text) + len(text_to_append)) > MESSAGE_LENGTH_LIMIT:
                    break
                text += text_to_append
            text = text[:-1] + '.'

        if data['answer_completeness'] != AnswerCompleteness.FULL.value.id:
            results_names.insert(0, {'id': flower_data['id'], 'name': flower_data['name']})

        if data['images_scan_permission'] and confidence >= 0.75:
            with open(image_path, 'rb') as f:
                requests.post(
                    f'{MODEL_ENDPOINT}/scan',
                    files={'file': f},
                    params={'label': flower_id, 'user_id': message.from_user.id},
                )

        await loading_msg.edit_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=None if len(results_names) == 0 else learn_more_keyboard(results_names)
        )
    elif response.status_code == 404:
        await loading_msg.edit_text(text=f'<i>Sorry, this flower has no info in database yet (id: <b>{flower_id + 1}</b>)</i>', parse_mode=ParseMode.HTML)
    else:
        await loading_msg.edit_text(text=f'<i>Sorry, the server is down (but here\'s the flower id: <b>{flower_id + 1}</b>)</i>', parse_mode=ParseMode.HTML)
    os.remove(image_path)

# Learn more callback
@router.callback_query(F.data.startswith('learn_more_'))
async def learn_more_handler(callback: CallbackQuery):
    loading_msg = await callback.message.answer('Loading...')
    data = callback.data.removeprefix('learn_more_')
    choice = int(data)
    response = requests.get(f'{API_ENDPOINT}/flowers/{choice}/?format=json')
    if response.status_code == 200:
        flower_data = response.json()
        text = f'<b>{flower_data['name']}</b>: {flower_data['long_description']}'
        await loading_msg.edit_text(text, parse_mode=ParseMode.HTML)
    else:
        await loading_msg.edit_text('Sorry, the server is down. Please try again later.', parse_mode=ParseMode.HTML)

# Back callback
@router.callback_query(F.data == 'back_to_settings')
async def back_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        text='Which setting do you want to modify?',
        reply_markup=settings_keyboard()
    )

# Cancel callback
@router.callback_query(F.data == 'cancel_settings')
async def cancelled_settingshandler(callback: CallbackQuery):
    await callback.message.edit_text('Settings modification cancelled.')

# Awareness completeness callback
@router.callback_query(F.data.startswith('answer_completeness_'))
async def answer_completeness_selected_handler(callback: CallbackQuery):
    await callback.message.edit_text('Loading...')
    data = callback.data.removeprefix('answer_completeness_')
    if (data == 'settings'):
        await callback.message.edit_text(
            text='Choose the desired answer completeness mode',
            reply_markup=answer_completeness_keyboard(API_ENDPOINT, callback)
        )
    else:
        choice = next((ac for ac in AnswerCompleteness if ac.value.id == int(data)), AnswerCompleteness.SHORT).value
        response = requests.patch(f'{API_ENDPOINT}/telegram-users/{callback.from_user.id}/', json={'answer_completeness': choice.id})
        if response.status_code == 200 or response.status_code == 201:
            await callback.message.edit_text(f'Changed answer completeness to: {choice.name.lower()}.')
        else:
            await callback.message.edit_text('Sorry, the server is down. Please try again later.')

# Probability threshold callback
@router.callback_query(F.data.startswith('probability_threshold_'))
async def probability_threshold_selected_handler(callback: CallbackQuery):
    await callback.message.edit_text('Loading...')
    data = callback.data.removeprefix('probability_threshold_')
    if data == 'settings':
        await callback.message.edit_text(
            text='Adjust the desired probability threshold for multiple classification results to appear',
            reply_markup=probability_threshold_keyboard(API_ENDPOINT, callback)
        )
    elif data.startswith('submit_'):
        choice = int(data.removeprefix('submit_'))
        response = requests.patch(f'{API_ENDPOINT}/telegram-users/{callback.from_user.id}/', json={'probability_threshold': choice})
        if response.status_code == 200 or response.status_code == 201:
            await callback.message.edit_text(f'Changed probability threshold to: {choice}%.')
        else:
            await callback.message.edit_text('Sorry, the server is down. Please try again later.')
    else:
        choice = int(data)
        choice = max(MIN_PROBABILITY_THRESHOLD, min(MAX_PROBABILITY_THRESHOLD, choice))
        await callback.message.edit_text(
            text=f'Adjust the desired probability threshold for multiple classification results to appear',
            reply_markup=probability_threshold_keyboard(API_ENDPOINT, callback, choice)
        )

# Privacy permission callback
@router.callback_query(F.data.startswith('privacy_permission_'))
async def privacy_permission_selected_handler(callback: CallbackQuery):
    await callback.message.edit_text('Loading...')
    choice = callback.data.removeprefix('privacy_permission_')
    if choice == 'settings':
        await callback.message.edit_text(
            text='Flower Classifier Bot can use your images to improve the quality of the neural network model. Your images will be stored in remote server after classification, deleted after training cycle at 0:00 UTC, and never transitioned to third parties.\nYou can toggle this permission at any time.',
            reply_markup=privacy_keyboard(API_ENDPOINT, callback)
        )
    else:
        response = requests.patch(f'{API_ENDPOINT}/telegram-users/{callback.from_user.id}/', json={'images_scan_permission': True if choice == 'enable' else False})
        if response.status_code == 200 or response.status_code == 201:
            await callback.message.edit_text(f'Privacy permission set to: {choice}.')
        else:
            await callback.message.edit_text('Sorry, the server is down. Please try again later.')

# Fallback
@dp.message()
async def fallback_handler(message: Message):
    await message.answer(f'Sorry, I can only interact with photos and commands.\nYou sent: {message.content_type.removeprefix('ContentType.').lower()}.')

# Main thread
async def main() -> None:
    await dp.start_polling(bot)

async def on_startup(bot: Bot):
    print(f'Bot is ready and running: {bot.id}')

dp.startup.register(on_startup)
dp.include_router(router)

asyncio.run(main())
