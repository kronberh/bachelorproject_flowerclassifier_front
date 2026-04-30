from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import CallbackQuery
import requests
from typing import Any
from enums import AnswerCompleteness

def settings_keyboard():
    builder = InlineKeyboardBuilder()

    builder.button(
        text='Answer completeness',
        callback_data='answer_completeness_settings'
    )

    builder.button(
        text='Probability threshold',
        callback_data='probability_threshold_settings'
    )

    builder.button(
        text='Privacy settings',
        callback_data='privacy_permission_settings'
    )

    builder.button(
        text='Cancel',
        callback_data='cancel_settings'
    )

    builder.adjust(1)
    return builder.as_markup()

def answer_completeness_keyboard(endpoint: str, callback: CallbackQuery):
    current_answer_completeness = None
    response = requests.get(f'{endpoint}/telegram-users/{callback.from_user.id}/?format=json')
    if (response.status_code == 200):
        data = response.json()
        current_answer_completeness = data['answer_completeness']

    builder = InlineKeyboardBuilder()

    for completeness in AnswerCompleteness:
        builder.button(
            text=f'{completeness.value.name}{' (current)' if current_answer_completeness == completeness.value.id else ''}',
            callback_data=f'answer_completeness_{completeness.value.id}'
        )
    
    builder.button(
        text='Back',
        callback_data='back_to_settings'
    )

    builder.adjust(3, 1)
    return builder.as_markup()

def probability_threshold_keyboard(endpoint: str, callback: CallbackQuery, current_probability_threshold: int = None):
    if (current_probability_threshold is None):
        response = requests.get(f'{endpoint}/telegram-users/{callback.from_user.id}/?format=json')
        if (response.status_code == 200):
            data = response.json()
            current_probability_threshold = data['probability_threshold']

    builder = InlineKeyboardBuilder()

    builder.button(
        text='-10',
        callback_data=f'probability_threshold_{current_probability_threshold - 10}'
    )

    builder.button(
        text='-5',
        callback_data=f'probability_threshold_{current_probability_threshold - 5}'
    )

    builder.button(
        text='-1',
        callback_data=f'probability_threshold_{current_probability_threshold - 1}'
    )

    builder.button(
        text='+1',
        callback_data=f'probability_threshold_{current_probability_threshold + 1}'
    )

    builder.button(
        text='+5',
        callback_data=f'probability_threshold_{current_probability_threshold + 5}'
    )

    builder.button(
        text='+10',
        callback_data=f'probability_threshold_{current_probability_threshold + 10}'
    )

    builder.button(
        text=f'Submit ({current_probability_threshold}%)',
        callback_data=f'probability_threshold_submit_{current_probability_threshold}'
    )

    builder.button(
        text=f'Back',
        callback_data='back_to_settings'
    )

    builder.adjust(6, 2)
    return builder.as_markup()

def privacy_keyboard(endpoint: str, callback: CallbackQuery):
    current_privacy_permission = None

    response = requests.get(f'{endpoint}/telegram-users/{callback.from_user.id}/?format=json')
    if (response.status_code == 200):
        data = response.json()
        current_privacy_permission = data['images_scan_permission']

    builder = InlineKeyboardBuilder()

    builder.button(
        text='Disable' if current_privacy_permission else 'Enable',
        callback_data=f'privacy_permission_{'disable' if current_privacy_permission else 'enable'}'
    )

    builder.button(
        text='Back',
        callback_data='back_to_settings'
    )

    builder.adjust(2)
    return builder.as_markup()

def learn_more_keyboard(flowers: list[Any]):
    builder = InlineKeyboardBuilder()
        
    for flower in flowers:
        builder.button(
            text=f'Learn more about {flower['name']}',
            callback_data=f'learn_more_{flower['id']}'
        )

    builder.adjust(1)
    return builder.as_markup()