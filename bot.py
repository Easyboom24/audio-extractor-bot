#from config import TOKEN
import ffmpeg
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher import FSMContext
from datetime import datetime
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.middlewares.logging import LoggingMiddleware
import streamlit as st
from asyncio import new_event_loop, set_event_loop
set_event_loop(new_event_loop())

# Configure logging
logging.basicConfig(level=logging.INFO)
# Initialize bot and dispatcher
bot = Bot(token=st.secrets["TOKEN"])

dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())

class MachineStates(StatesGroup):
    IN_PROCESS = State()
    VIDEO = State()
    AUDIO = State()
    ALL = State()

kb = [
    [types.KeyboardButton(text='📹 Видео без звука')],
    [types.KeyboardButton(text="🔈 Аудио без видео")],
    [types.KeyboardButton(text="🔈📹 Звук и видео по отдельности")],
    [types.KeyboardButton(text="❌ Отмена")],
]

@dp.message_handler(commands=['start'])
async def command_start(message: types.Message):
    await message.answer("Привет!\nЯ умею отделять аудио от видео и наоборот!\nПриступим!\nОтправьте мне видео размером до 50мб")
    
@dp.message_handler(state=None, content_types=['video'])
async def download_video(message: types.Message, state: FSMContext):
    try:
        file_id = message.video.file_id
        file = await bot.get_file(file_id)
        datestamp = str(datetime.now()).replace('.','-').replace(' ', '-').replace(':', '-')
        await bot.download_file(file.file_path, f"videos/video-{datestamp}.mp4")
        async with state.proxy() as data:
            data['datestamp'] = datestamp
        await MachineStates.IN_PROCESS.set()
        keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
        await message.answer("Что Вы хотите получить?", reply_markup=keyboard)
    except:
        await message.answer("Что-то пошло не так!")
        await state.finish()

@dp.message_handler(Text(equals='📹 Видео без звука', ignore_case=True), state=MachineStates.IN_PROCESS)
async def set_state_video(message: types.Message, state: FSMContext):
    await MachineStates.VIDEO.set()
    msg = await message.answer("Подождите, пожалуйста...", reply_markup=types.ReplyKeyboardRemove())
    await get_video(message,state, msg)

@dp.message_handler(Text(equals='🔈 Аудио без видео', ignore_case=True), state=MachineStates.IN_PROCESS)
async def set_state_video(message: types.Message, state: FSMContext):
    await MachineStates.AUDIO.set()
    msg = await message.answer("Подождите, пожалуйста...", reply_markup=types.ReplyKeyboardRemove())
    await get_audio(message,state,msg)

@dp.message_handler(Text(equals='🔈📹 Звук и видео по отдельности', ignore_case=True), state=MachineStates.IN_PROCESS)
async def set_state_video(message: types.Message, state: FSMContext):
    await MachineStates.ALL.set()
    msg = await message.answer("Подождите, пожалуйста...", reply_markup=types.ReplyKeyboardRemove())
    await get_all(message,state,msg)

@dp.message_handler(Text(equals='❌ Отмена', ignore_case=True), state=MachineStates.IN_PROCESS)
async def cancel(message: types.Message, state: FSMContext):
    await message.answer(text="Действие с загруженным видео отменено.\nЕсли хотите попробовать ещё раз, загрузите видео снова",reply_markup=types.ReplyKeyboardRemove())
    await state.finish()

async def get_video(message: types.Message, state: FSMContext, msg:  types.Message):
    async with state.proxy() as data:
        input = ffmpeg.input(f"videos/video-{data['datestamp']}.mp4")
        videoFile = input.video
        ffmpeg.output(videoFile,f"outputVideo/{data['datestamp']}.mp4").run()
        await message.reply_video(open(f"outputVideo/{data['datestamp']}.mp4", "rb"))
        await msg.delete()
    await state.finish()

async def get_audio(message: types.Message, state: FSMContext, msg:  types.Message):
    async with state.proxy() as data:
        input = ffmpeg.input(f"videos/video-{data['datestamp']}.mp4")
        audioFile = input.audio
        ffmpeg.output(audioFile,f"outputAudio/{data['datestamp']}.mp3").run()
        await message.reply_audio(open(f"outputAudio/{data['datestamp']}.mp3", "rb"))
        await msg.delete()
    await state.finish()

async def get_all(message: types.Message, state: FSMContext, msg:  types.Message):
    async with state.proxy() as data:
        input = ffmpeg.input(f"videos/video-{data['datestamp']}.mp4")
        audioFile = input.audio
        videoFile = input.video
        ffmpeg.output(videoFile,f"outputVideo/{data['datestamp']}.mp4").run()
        ffmpeg.output(audioFile,f"outputAudio/{data['datestamp']}.mp3").run()
        await message.reply_video(open(f"outputVideo/{data['datestamp']}.mp4", "rb"))
        await message.reply_audio(open(f"outputAudio/{data['datestamp']}.mp3", "rb"))
        await msg.delete()
    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
