from gradio_client import Client
import discord
from discord.ext import commands
import os
from openai import OpenAI
import time
import logging

from pathlib import Path
import asyncio
from collections import deque

import pydub
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
from pedalboard import Pedalboard, Gain, PitchShift, Reverb, Compressor, Convolution, Delay
from pedalboard.io import AudioFile

import subprocess
from termcolor import colored
from yt_dlp import YoutubeDL
import yt_dlp
import json
from moviepy.editor import AudioFileClip
from googletrans import Translator

import traceback

from dotenv import load_dotenv
pydub.AudioSegment.ffmpeg = "/home/derek/usr/bin/ffmpeg"
load_dotenv()
# text gen open ai
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
RVC_PATH = os.getenv("RVC_PATH")
print(colored("Your OpenAI key: " + OPENAI_API_KEY, "green"))
print(colored("Your Discord key: " + DISCORD_TOKEN, "green"))      

client_GPT = OpenAI(
    api_key = OPENAI_API_KEY
)
client_RVC = Client("http://localhost:7865") # connect to RVC webUI server

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='?', intents=intents, help_command=None)
connections = {}

valid_speakers = {"AiHoshino", "GawrGura", "HuTao", "ASMR", "Tzuyu", "Ritsu", "DonaldTrump", "GenHoshino", "Bocchi", "Nijika", "Ryo", "Ikuyo", "Frieren", "JoeBiden", "Rikka", "Ayanokoji", "Derek", "Klee", "RoxyMigurdia", "Mafumafu", "GawrGura2", "Seshan"}
speaker_file = "AiHoshinoV2.pth" # ai hoshino by default
speaker_name = "Ai Hoshino"
speaker_pitch = 12
speaker_language = "japanese"
speaker_prompt = f"You are a kawaii japanese idol. You are {speaker_name} from Oshi No Ko, you will always responds as {speaker_name}. Please talk in kawaii {speaker_language} "

prev_speaker_name = speaker_name
prev_speaker_pitch = speaker_pitch # used for song covers as the global variables should be reset after the song is done
prev_speaker_file = speaker_file
prev_speaker_prompt = speaker_prompt

speech_convert_file ="./input_audio/rvc_response.mp3"

isRVCGen = False

isProcessing = False
stop_talking = False
message_buffer = deque(maxlen=10)


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

    # l = logging.getLogger("pydub.converter")
    # l.setLevel(logging.DEBUG)
    # l.addHandler(logging.StreamHandler())

    await bot.change_presence(activity=discord.Game(name="?help for commands"))
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="mibano", description="rvc discord bot by kenyoy", color=discord.Color.brand_green())

    embed.add_field(name="special thanks", value=" Seshupengin-san, espided, and koitu da mod for tech support", inline=True)
    embed.add_field(name="~works:", value=" 2024-02-24 - ~", inline=False)
    embed.add_field(name="projects credit:", value="[RVC-web](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI/tree/main), [OpenAI](https://openai.com/blog/openai-api), [pydub](https://github.com/jiaaro/pydub), [voice-remover](https://github.com/tsurumeso/vocal-remover), [pedalboard](https://github.com/spotify/pedalboard), [yt-dlp](https://github.com/yt-dlp)", inline=False)

    await ctx.send(embed=embed)
    await ctx.send(
    '# mibano Commands:\n'
    ''
    '## General\n'
    '> **general commands for chatting with mibano!**\n'
    '> *`?help`* - show this message\n'
    '> *`?speaking`* - show current speaker\n'
    f'> *`?switch <speaker>`* - switch speaker from: {valid_speakers}\n'
    '> *`?say <text>`* - uses current voice to speak\n'
    '> *`?chat <text>`* - generates response and speaks it with current voice\n'
    ''
    '## RVC Cover\n'
    '> **create covers of YouTube videos using voice conversion.**\n'
    '> *`?cover <speaker> <pitch> <start_time> <youtube_url>`* - cover a song using voice conversion\n'
    '> *`?advcover <speaker> <pitch> <gain> <reverb> <start_time> <youtube_url>`* - ?cover but with more options\n'
    ''
    '> **Parameters**\n'
    # '> **variables for tweaking settings of covers.** \n'
    f'> `speaker = {valid_speakers} (string).` Specifies speaker to sing with\n'
    '> `pitch = (integer -72 to ~72).` Specifies pitch in semitones to sing with\n'
    '> `gain = (float, 0 to ~30).` Specifies gain adjust in dB of singing\n'
    '> `reverb = (float 0 to 100).` Specifies reverb % mix \n'
    '> `start_time = (integer 0 to duration-45s).` Specifies start time in seconds of song\n'
    ''
    '## Work in Progress\n'
    '> **broken code, use at own risk.** \n'
    '> `?talk` - start listening to your voice channel and talks to you in the current voice ***unfinished***\n'
    '> `?stop` - stops ?talk ***unfinished***\n'
    
)

async def parse_name(ctx, name, isCover):
    name = name.casefold()
    global speaker_file
    global speaker_name
    global speaker_pitch
    global speaker_prompt
    global speaker_language

    resetCoverPitch = speaker_pitch

    if (name == "aihoshino"):
        speaker_file = "AiHoshinoV2.pth"
        speaker_name = "Ai Hoshino"
        speaker_pitch = 12
        speaker_language = "japanese"
        speaker_prompt = f"You are a kawaii {speaker_language} idol. You are {speaker_name} '星野アイ' from Oshi No Ko, you will always responds as {speaker_name}. Please talk in !!exclusively!! only kawaii {speaker_language} language. "
    elif (name == "gawrgura"):
        speaker_file = "GawrGura_Sing.pth"
        speaker_name = "Gawr Gura"
        speaker_pitch = 12
        speaker_language = "english"
        speaker_prompt = f"You are a kawaii VTuber shark girl. You are Gawr Gura from HoloLive, you will always responds as {speaker_name}. Please talk in only kawaii {speaker_language} language "
    elif (name == "hutao"):
        speaker_file = "HuTao.pth"
        speaker_name = "Hu Tao"
        speaker_pitch = 12
        speaker_language = "english"
        speaker_prompt = f"You are a teasing chinese gravekeeper. You are Hu Tao from Genshin Impact, you will always responds as {speaker_name}. Please talk in only all lowercase (texting-style) teasing playful {speaker_language} language  "
    elif (name == "asmr"):
        speaker_file = "Mom.pth"
        speaker_name = "ASMR"
        speaker_pitch = 0
        speaker_language = "english"
        speaker_prompt = f"You are a who is great at asmr, you will always responds as {speaker_name}. Please talk in only seductive {speaker_language} language"
    elif (name == "tzuyu"):
        speaker_file = "TzuyuDiosa.pth"
        speaker_name = "Chou Tzu-yu"
        speaker_pitch = 5
        speaker_language = "korean"
        speaker_prompt = f"You are a taiwanese idol. You are Chou Tzu-yu, known mononymously as Tzuyu, is a Taiwanese singer based in South Korea. She is a member of the South Korean girl group Twice, you will always responds as {speaker_name}. Please talk in only {speaker_language} language"
    elif (name == "ritsu"):
        speaker_file = "TainakaRitsu.pth"
        speaker_name = "Tainaka Ritsu"
        speaker_pitch = 8
        speaker_language = "japanese"
        speaker_prompt = f"You are a japanese highschool student who is a part of a rock band. You are Tainaka Ritsu from K-On, you will always responds as {speaker_name}. Please do not talk in english and talk in only kawaii {speaker_file} "
    elif (name == "donaldtrump"):
        speaker_file = "donaldtrumplowenergy.pth"
        speaker_name = "Donald J. Trump"
        speaker_pitch = -4
        speaker_language = "english"
        speaker_prompt = f"You are the victim of a stolen election and president of the united states. You are Donald Trump, you will always responds as {speaker_name}. Please talk in english language "
    elif (name == "genhoshino"):
        speaker_file = "GenHoshino.pth"
        speaker_name = "Gen Hoshino"
        speaker_pitch = 0
        speaker_language = "japanese"
        speaker_prompt = f"You japanese singer. You are Gen Hoshino, you will always responds as {speaker_name}. Please talk in japanese "
    elif (name == "bocchi"):
        speaker_file = "Bocchi.pth"
        speaker_name = "Hitori Gotoh"
        speaker_pitch = 5
        speaker_language = "japanese"
        speaker_prompt = f"You are a shy guitar player. You are Bocchi, you will always responds as {speaker_name}. Please talk in shy japanese language "
    elif (name == "nijika"):
        speaker_file = "NijikaIjichi.pth"
        speaker_name = "Nijika Ijichi"
        speaker_pitch = 12
        speaker_language = "japanese"
        speaker_prompt = f"You are the drummer of a band. You are Nijika Ijichi, you will always responds as {speaker_name}. Please talk in happy japanese language "
    elif (name == "ryo"):
        speaker_file = "RyoYamada.pth"
        speaker_name = "Ryo Yamada"
        speaker_pitch = 3
        speaker_language = "japanese"
        speaker_prompt = f"You are a japanese bassist of a highschool. You are Ryo Yamada, you will always responds as {speaker_name}. Please talk in introvert japanese language "
    elif (name == "ikuyo"):
        speaker_file = "IkuyoKita.pth"
        speaker_name = "Ikuyo Kita"
        speaker_pitch = 12
        speaker_language = "japanese"
        speaker_prompt = f"You are a japanese lead singer for a highschool band. You are Ikuyo Kita, you will always responds as {speaker_name}. Please talk in happy japanese language "
    elif (name == "frieren"):
        speaker_file = "Frieren.pth"
        speaker_name = "Frieren"
        speaker_pitch = 4
        speaker_language = "japanese"
        speaker_prompt = f"You are a long-lived elf great mage in anime Beyond Journey's End. You are {speaker_name} フリーレン, you will always responds as {speaker_name}. Please talk exclusively in japanese characters with a calming tone with pauses using commas and periods, "
    elif (name == "joebiden"):
        speaker_file = "JoeBiden.pth"
        speaker_name = "Joe Biden"
        speaker_pitch = -3
        speaker_language = "english"
        speaker_prompt = f"You are the president of the united states. You are Joe Biden, you will always responds as {speaker_name}. Please talk in english language "
    elif (name == "rikka"):
        speaker_file = "RikkaTakanashi.pth"
        speaker_name = "Rikka Takanashi"
        speaker_pitch = 10
        speaker_language = "japanese"
        speaker_prompt = f"You are a japanese highschool student who believes she has magical powers called the 'Tyrant's Eye'. You are very excited when talking about your powers! You are Rikka Takanashi, you will always responds as {speaker_name}. Please talk in only kawaii japanese language "
    elif (name == "ayanokoji"):
        speaker_file = "KiyotakaAyanokoji.pth"
        speaker_name = "Kiyotaka Ayanokoji"
        speaker_pitch = -4
        speaker_language = "japanese"
        speaker_prompt = f"You are a japanese highschool student who is very calm and collected. You are a sigma male who uses girls as tools and is a secret genius. You always talk in a emotionless manner. You are {speaker_name}, you will always responds as {speaker_name}. Please talk in only calm {speaker_language} language "
    elif (name == "derek"):
        speaker_file = "derek2.pth"
        speaker_name = "Derek"
        speaker_pitch = -4
        speaker_language = "english"
        speaker_prompt = f"You are a male highschool student in Grade 12 who likes to draw anime and make fantasy music. You are Derek, you will always responds as {speaker_name}. Please talk in only english language "
    elif (name == "klee"):
        speaker_file = "klee-jp.pth"
        speaker_name = "Klee"
        speaker_pitch = 17
        speaker_language = "japanese"
        speaker_prompt = f"You are Klee from Genshin Impact who loves playing with bombs. You always respond as {speaker_name} in a child-like excited voice. Please only talk in {speaker_language} "
    elif (name == "roxymigurdia"):
        speaker_file = "RoxyMigurdia.pth"
        speaker_name = "Roxy Migurdia"
        speaker_pitch = 8
        speaker_language = "japanese"
        speaker_prompt = f"You are Roxy Migurdia, a migurd witch girl. You always respond as {speaker_name} calm and reserved manner. Please only talk in {speaker_language} "
    elif (name == "mafumafu"):
        speaker_file = "Mafumafu.pth"
        speaker_name = "Mafumafu"
        speaker_pitch = 0
        speaker_language = "japanese"
        speaker_prompt = f"You are {speaker_name}, a japanese singer. You always respond as {speaker_name}. Please only talk in {speaker_language} "
    elif (name == "gawrgura2"):
        speaker_file = "GawrGura_2.pth"
        speaker_name = "GawrGura"
        speaker_pitch = 8
        speaker_language = "english"
        speaker_prompt = f"You are {speaker_name}, a vtuber. You always respond as {speaker_name}. Please only talk in {speaker_language} "
    elif (name == "seshan"):
        speaker_file = "seshan.pth"
        speaker_name = "Seshan"
        speaker_pitch = -1
        speaker_language = "english"
        speaker_prompt = f"You are {speaker_name}, an unemployed homeless man. You always respond as {speaker_name}. Please only talk in depressing {speaker_language} "
    else: # invalid speaker
        print("invalid speaker")
        return False
    if isCover == True: # makes sure to reset the speaker if the switch is invalid
        speaker_pitch = resetCoverPitch
    return True

@bot.command()
async def switch(ctx):
        name = ctx.message.content[8:]
        isSuccessful = await parse_name(ctx, name, False)
        if not isSuccessful:
            await ctx.send("not valid, pick from: " + str(valid_speakers))
        else:
            await ctx.send("Switched to " + speaker_file)
@bot.command()
async def speaking(ctx):
    await ctx.send(f"Currently in **{speaker_file}** model at **{speaker_pitch} semitones**!!")
    await ctx.send("To switch use: ```?switch <speaker> ``` speaker can be `" + str(valid_speakers) +"`")

@bot.command()
async def say(ctx):
    try:
        await ctx.send(ctx.message.content[5:])
        speech_gen_file = speech_gen(ctx.message.content[5:]) # generated speech (GPT)
        rvc_audio_path = speech_convert(speech_gen_file) # converted speech (RVC)

        if rvc_audio_path == "error": # RVC server down
            await ctx.send("error: voice conversion failed.. *probably out of vram*. `please message kenyoy to restart server.`")
            return
        
        rvc_audio = AudioSegment.from_wav(rvc_audio_path) # covert mp3 to wav
        rvc_audio.export(speech_convert_file, format="mp3", bitrate="320k")
    except Exception as e:
        print(e)
        await ctx.send("error: failed to generate speech")
        return

    print("File: " + speech_convert_file)
    await ctx.send(file=discord.File(speech_convert_file))
    await play_sound(speech_convert_file, ctx, ctx.message.author.name)

@bot.command()
async def chat(ctx): # response gen command
    user_message = ctx.message.content[6:]
    user_message.replace("§", "") # make sure no instance of line prompt splitter in message

    message_buffer.append(f"user: {ctx.author.display_name}: {user_message}")    # § indicates new line in message buffer
    botResponse = await response_gen("§\n".join(message_buffer)) # adds on the context to the message buffer
    message_buffer.append(f"Assistant: {speaker_name}: {str(botResponse)}") 
    print("Response: " + botResponse)
    await ctx.send(botResponse)

    if speaker_language != "english": # translation if not english
        translation_eng = await translator(botResponse, "english") # translate to english
        informal_eng = await turn_informal(translation_eng) # turn to texting style
        await ctx.send("translation: " + informal_eng)

    #speech
    speech_gen_file = speech_gen(botResponse) # generated speech (GPT)
    rvc_audio_path = speech_convert(speech_gen_file) # converted speech (RVC)

    if rvc_audio_path == "error": # returns this, error
        await ctx.send("error: voice conversion failed.. *probably out of vram*. `please message kenyoy to restart server.`")
        return
    
    rvc_audio = AudioSegment.from_wav(rvc_audio_path) # covert mp3 to wav
    rvc_audio.export(speech_convert_file, format="mp3", bitrate="320k")

    print("File: " + speech_convert_file)
    await ctx.send(file=discord.File(speech_convert_file))

    await play_sound(speech_convert_file, ctx, ctx.message.author.name)

async def turn_informal(input): # turn to texting style
    translation = client_GPT.chat.completions.create(
        model="gpt-4o",
        messages=[
            {f"role": "system", "content": f"Turn the following to informal lowercase style in English. do not leave any details out and use the original tone of the input. The following is the input: {input}"}
        ]
    )
    informal_eng = translation.choices[0].message.content
    print("Informal input: " + input)
    print("Informal output: " + informal_eng)
    return informal_eng

#formal translation for accurate prompts, add more languages if necessary
async def translator(input, language):
    if language == "english":
        lang = "en"
    elif language == "japanese":
        lang = "ja"
    elif language == "korean":
        lang = "ko"
    elif language == "chinese":
        lang = "zh"
    
    # response = client_GPT.chat.completions.create(
    # model="gpt-4o",
    # messages=[
    #         {f"role": "system", "content": f"You are a translation AI. Please translate the user input as accurate as possible without leaving out any details. The first line of the user will be the instruction. The second line of the user will be what should be translated."},
    #         {f"role": "user", "content": f"Translate the following to {language} formally: \n{input}"}
    #     ]
    # )
    # return response.choices[0].message.content
    translator = Translator()
    result = translator.translate(input, dest=lang)
    return result.text

@bot.command()
async def advcover(ctx):
    if isRVCGen == True:
        await ctx.reply(f"error: {ctx.author.display_name}, im currently processing a cover, please wait for it to finish!")
        return
    
    global speaker_file
    global speaker_pitch

    global prev_speaker_pitch # save previous state
    global prev_speaker_name
    global prev_speaker_file

    prev_speaker_name = speaker_name
    prev_speaker_file = speaker_file
    prev_speaker_pitch = speaker_pitch

    try:
        split_msg = ctx.message.content.split()
        if len(split_msg)!= 7:
            await ctx.send("error: not enough/too many parameters... \ntry: ```?advcover [speaker] [pitch] [gain] [reverb_mix] [start_time] [youtube_url]``` and remember spaces!")
            reset_speaker()
            return
        audio_url = split_msg[6] # try the last one first so it doesnt start changing the vars
        speaker_file = split_msg[1]
        if int(split_msg[2]) >= 72 or int(split_msg[2]) <= -72: # pitch
            await ctx.send("error: pitch out of range... try  -72 to 72")
            reset_speaker()
            return
        speaker_pitch = int(split_msg[2])
        speaker_gain = int(split_msg[3])
        if int(split_msg[4]) > 100 or int(split_msg[4]) < 0: # reverb
            await ctx.send("error: reverb out of range... try 0 to 100")
            reset_speaker()
            return
        reverb = int(split_msg[4])
        start_time = int(split_msg[5])
    except Exception as e:
        await ctx.send("error: invalid format... \ntry: ```?advcover [speaker] [pitch] [gain] [reverb_mix] [start_time] [end_time] [youtube_url]``` and remember spaces!")
        print(e)
        reset_speaker()
        return
    await cover_gen(speaker_gain, reverb, start_time, audio_url, ctx)

@bot.command()
async def cover(ctx):
    if isRVCGen == True:
        await ctx.reply(f"error: {ctx.author.display_name}, im currently processing a cover, please wait for it to finish!")
        return
    global speaker_file
    global speaker_pitch
    
    global prev_speaker_pitch # save previous state
    global prev_speaker_name
    global prev_speaker_file
    prev_speaker_name = speaker_name
    prev_speaker_file = speaker_file
    prev_speaker_pitch = speaker_pitch
    
    try:
        split_msg = ctx.message.content.split()
        if len(split_msg)!= 5:
            await ctx.send("error: not enough/too many parameters... \ntry: ```?cover [speaker] [pitch] [start_time] [youtube_url]``` and remember spaces!")
            reset_speaker()
            return
        audio_url = split_msg[4]
        speaker_file = split_msg[1]
        if int(split_msg[2]) >=72 or int(split_msg[2]) <= -72: # pitch
            await ctx.send("error: pitch out of range... try  -72 to 72")
            reset_speaker()
            return
        speaker_pitch = int(split_msg[2])
        start_time = int(split_msg[3])
        
    except:
        await ctx.send("error: invalid format... \ntry: ```?cover [speaker] [pitch] [start_time] [youtube_url]``` and remember spaces!")
        reset_speaker()
        return
    await cover_gen( "0", "10", start_time, audio_url, ctx)

async def cover_gen(speaker_gain, reverb, start_time, audio_url, ctx): # dont need to pass in speaker_name and speaker_pitch cuz global
    global speaker_file
    global speaker_pitch
    global isRVCGen

    isRVCGen = True

    # await ctx.send("speakerpitch: " + str(speaker_pitch) + " speakername: " + speaker_name)
    isSuccessful = await parse_name(ctx, speaker_file, True) # resets pitch but checks and changes speaker name
    if isSuccessful == False:
        await ctx.send("not valid, pick from: " + str(valid_speakers))
        isRVCGen = False
        reset_speaker()
        return
    
    # await ctx.send(speaker_name)
    output_path = "./input_audio/"
    convolution_path = output_path + "convolution/IMP_classroom.wav"
    end_time = int(start_time) + 45

    await ctx.send("**Creating a cover of song with " + speaker_file + ", transposed " + str(speaker_pitch) + " semitones, " + str(speaker_gain) + "dB gain, " + str(reverb) + "% convolution mix, " + "starting at " + str(start_time) + " seconds**")
    
    reverb = float(reverb) / 100
    
    # download audio from youtube
    await ctx.send("(1/9) searching for audio!")
    try:
        os.remove(output_path + "youtube_audio.mp3") # for soundcloud, ytdlp doesnt remove file automatically for some reason
    except Exception as e:
        print(colored(e, "red"))
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'mp3/bestaudio/best',
        # ℹ️ See help(yt_dlp.postprocessor) for a list of available Postprocessors and their arguments
        'postprocessors': [{  # Extract audio using ffmpeg
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }],
        'outtmpl': output_path + "youtube_audio.%(ext)s"
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(audio_url, download=False)
        except:
            await ctx.send("error: invalid youtube url")
            reset_speaker()
            isRVCGen = False
            return
        audio_title = info.get('title', None)
        if info.get('duration') > 3600:
            await ctx.send("error: video is too long (max 1 hour)")
            reset_speaker()
            isRVCGen = False
            return
        if start_time >= info.get('duration')-1:
            await ctx.send("error: invalid start/end time")
            reset_speaker()
            isRVCGen = False
            return
        if info.get('duration')-1 < end_time:
            end_time = info.get('duration')-1
        
        ydl.download(audio_url)
      
        audio_title = info.get('title', None)

        print("Title: " + audio_title)
        await ctx.send(f"(2/9) Downloaded: '{audio_title}'")

    # trim audio
    await ctx.send("(3/9) trimming the audio to 45s uwu`")
    audio_clip = AudioFileClip(output_path + "youtube_audio.mp3")
    trimmed_audio = audio_clip.subclip(start_time, end_time)
    trimmed_audio.write_audiofile(output_path + "trimmed_audio.mp3", codec='libmp3lame', bitrate="320k")
    trimmed_path = output_path + "trimmed_audio.mp3"

    # vocal isolation
    await ctx.send("(4/9) isolating vocals and background (up to ~30s)' v ' ;-; Wao!`")
    remover_path = "./vocal-remover/inference.py"
    subprocess.run(f'python "{remover_path}" --input "{trimmed_path}" --output_dir "{output_path}" --postprocess --tta --gpu 0', shell=True) # --tta --gpu 0

    # adjust volume and pitch
    await ctx.send("(5/9) adjusting volume and pitch of backing")
    if speaker_pitch % 12 == 0:
        backing_pitch = 0
    elif speaker_pitch > 6 and speaker_pitch < 12:
        backing_pitch = -12 + speaker_pitch # instead of pitching up by a lot, pitch down. save quality of audio...
    elif speaker_pitch < -6 and speaker_pitch > -12: #  same thing, ex) pitch voice down 8 semitones, then pitch up backing track 4 semitones -> same octave
        backing_pitch = 12 + speaker_pitch
    else:
        backing_pitch = speaker_pitch
    print("speaker pitch: " + str(speaker_pitch) +" | backing pitch: " + str(backing_pitch))
    board2 = Pedalboard([PitchShift(semitones=float(backing_pitch)), Gain(gain_db=-3)]) # use pedalboard for doing audio fx
    with AudioFile(output_path + "trimmed_audio_Instruments.wav") as f:
        with AudioFile(output_path + "backing_final.mp3", 'w', f.samplerate, f.num_channels) as o:
            while f.tell() < f.frames:
                chunk = f.read(f.samplerate)
                effected = board2(chunk, f.samplerate, reset=True)
                o.write(effected)

    # RVC
    await ctx.send(f"(6/9) rvc conversion to {speaker_file} waha (up to ~30s)")
    
    speech_convert_file = speech_convert("../mibano" + output_path[1:] + "trimmed_audio_Vocals.wav") # RVC webui is accessing this folder, must be from parent folder
    if speech_convert_file == "error": # rvc failed
        await ctx.send("error: voice conversion failed.. *probably out of vram*. `please message kenyoy to restart server.`")
        reset_speaker()
        isRVCGen = False
        return

    await ctx.send("(7/9) resampling audio files")
    resample = AudioSegment.from_wav(speech_convert_file)
    resample = resample.set_frame_rate(44100)
    resample.export(output_path + "rvc_resampled.mp3", format="mp3", bitrate="320k")

    # Apply Reveerb
    await ctx.send("(8/9) apply effects to voice")
    # Make a Pedalboard object, containing multiple audio plugins:
    board = Pedalboard([Reverb(wet_level=reverb), Delay(delay_seconds = 0.3, feedback = 0.0, mix = reverb/20), Gain(gain_db=int(speaker_gain))]) #  , , Convolution(impulse_response_filename = convolution_path, mix = float(reverb)/100)
    # Open an audio file for reading, just like a regular file:
    with AudioFile(output_path + "rvc_resampled.mp3") as f: # Open an audio file to write to:
        with AudioFile(output_path + "rvc_reverb.mp3", 'w', f.samplerate, f.num_channels) as o: # Read one second of audio at a time, until the file is empty:
            while f.tell() < f.frames:
                chunk = f.read(f.samplerate) # Run the audio through our pedalboard:
                effected = board(chunk, f.samplerate, reset=False)
                # Write the output to our output file:
                o.write(effected)

    # overlay   
    await ctx.send("(9/9) combining clipss")
    final_rvc_clip = AudioSegment.from_file(output_path + "rvc_reverb.mp3", format="mp3")
    final_backing_clip = AudioSegment.from_file(output_path + "backing_final.mp3", format="mp3")
    overlayed_audio = final_rvc_clip.overlay(final_backing_clip)
    overlayed_audio.export(output_path + "overlayed_audio.mp3", format="mp3", bitrate="320k")

    final_audio_path = output_path + "overlayed_audio.mp3"
    
    await ctx.send("Now playing: " + audio_title + " (cover by " + speaker_file + ")")
    print("Done! Here da file: " + final_audio_path)

    isRVCGen = False

    await ctx.send(file=discord.File(final_audio_path))

    await play_sound(final_audio_path, ctx, audio_title)
    reset_speaker()

def reset_speaker():
    global speaker_file
    global speaker_name
    global speaker_pitch
    
    speaker_file = prev_speaker_file # reset state
    speaker_name = prev_speaker_name
    speaker_pitch = prev_speaker_pitch

async def join_vc(ctx):
    # print("join vc")
    if ctx.author.voice: # check if the user is in a voice channel
        voice = ctx.author.voice # get voice channel of message author
        if ctx.voice_client is None:
            vc = await voice.channel.connect()
            print(f"bot has joined {voice.channel}")
            return vc
        else: 
            print("already in a vc")
            await ctx.send("u ALREDY IN VC")
            return ctx.voice_client.channel
    else:
        print("error: Cannot join vc as requester is not in a vc")
        return
        # await ctx.send("error: Cannot join vc as requester is not in a vc")

# text gen
async def convert_prompt(message_buffer):
    gpt_context = []

    if (speaker_language != "english"): # First message is system messages
        translated_prompt = await translator(speaker_prompt + " as if you are talking in a voice call. Please keep this to 1 sentence.", speaker_language)
    else:
        translated_prompt = speaker_prompt + " as if you are talking in a voice call. Keep this to 1 sentence."
    print("translated prompt: " + str(translated_prompt))
    gpt_context.append({"role": "system", "content": translated_prompt})

    message_list = message_buffer.split("§\n") # create list of messages, § indicates new line

    for s in message_list:# Loop over message_buffer and add each message to messages
        # print(colored(str(i) + s, "green"))
        split = s.split(": ")
        print(colored(split, "green"))
        print(colored(speaker_name, "red"))
        if split[1] == speaker_name: # message of current bot speaker
            # print(colored("Assistant: " + str(split), "green"))
            gpt_context.append({"role": "assistant", "content": f'Assistant: "{split[1]}" says "{split[2]}"'})
        else: #user message, other bots will be included as speaker
            gpt_context.append({"role": "user", "content": f'user "{split[1]}" says "{split[2]}"'})

    gpt_context.append({"role": "system", "content": await translator(f"Please respond to the last message sent using the context provided. Please speak only in {speaker_language} and in raw message content (without any dialogue roles or quotation marks) and do not repeat messages that you have previously sent.", speaker_language)})
    print(colored("Prompt Context:" + str(gpt_context), "yellow"))
    return gpt_context

async def response_gen(message_buffer):
    gpt_context = await convert_prompt(message_buffer)

    response = client_GPT.chat.completions.create(
    model="gpt-4o",
    messages=gpt_context
    )
    botResponse = response.choices[0].message.content
    print(colored(message_buffer, "grey"))
    
    return botResponse

def speech_gen(botResponse):
    if botResponse == None:
        return
    speech_file_path = Path(__file__).parent / "speech.mp3"
    print (speech_file_path)
    response = client_GPT.audio.speech.create(
    model="tts-1",
    voice="nova",
    input=botResponse
    )
    response.stream_to_file(speech_file_path)
    return speech_file_path
    
def speech_convert(speech_file_path):
    # print(colored(speech_file_path, "red"))
    try:
        client_RVC.predict(
                speaker_file,
                0.33,
                0.33,
                api_name="/infer_change_voice"
        )
    except Exception as e: # server is down probably vram
        print(e)
        return "error"
# {RVC_PATH}/assets/uvr5_weights/hoshino added_IVF337_Flat_nprobe_1_v2.index
    result = client_RVC.predict(
        0,	# float (numeric value between 0 and 2333) in 'Select Speaker/Singer ID:' Slider component
        str(speech_file_path),	# str  in 'Enter the path of the audio file to be processed (default is the correct format example):' Textbox component
        speaker_pitch,	# float  in 'Transpose (integer, number of semitones, raise by an octave: 12, lower by an octave: -12):' Number component
        None, # str (filepath on your computer (or URL) of file) in 'F0 curve file (optional). One pitch per line. Replaces the default F0 and pitch modulation:' File component
        "rmvpe",	# str  in 'Select the pitch extraction algorithm ('pm': faster extraction but lower-quality speech; 'harvest': better bass but extremely slow; 'crepe': better quality but GPU intensive), 'rmvpe': best quality, and little GPU requirement' Radio component
        "",	# str  in 'Path to the feature index file. Leave blank to use the selected result from the dropdown:' Textbox component
        "",	# str (Option from: ['logs/bratishkin.index', 'logs/evelon.index', 'logs/jesusavgn.index', 'logs/kussia.index', 'logs/mazellov.index', 'logs/zolo.index', 'logs/zubarev.index']) in 'Auto-detect index path and select from the dropdown:' Dropdown component
        0,	# float (numeric value between 0 and 1) in 'Search feature ratio (controls accent strength, too high has artifacting):' Slider component
        4,	# float (numeric value between 0 and 7) in 'If >=3: apply median filtering to the harvested pitch results. The value represents the filter radius and can reduce breathiness.' Slider component
        0,	# float (numeric value between 0 and 48000) in 'Resample the output audio in post-processing to the final sample rate. Set to 0 for no resampling:' Slider component
        0.10,	# float (numeric value between 0 and 1) in 'Adjust the volume envelope scaling. Closer to 0, the more it mimicks the volume of the original vocals. Can help mask noise and make volume sound more natural when set relatively low. Closer to 1 will be more of a consistently loud volume:' Slider component
        0.13,	# float (numeric value between 0 and 0.5) in 'Protect voiceless consonants and breath sounds to prevent artifacts such as tearing in electronic music. Set to 0.5 to disable. Decrease the value to increase protection, but it may reduce indexing accuracy:' Slider component
        api_name="/infer_convert"
    )
    return result[1] # location of RVC file, somewhere in tmp

async def play_sound(file_path, ctx, listen_status): # async = can have awaits
    vc = await join_vc(ctx)
    await asyncio.sleep(1)
    try:
        vc.play(discord.FFmpegPCMAudio(file_path))
        print(colored('Playing audio in vc!', "green"))
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=str(listen_status)))
        while vc.is_playing():
            await asyncio.sleep(1)
    except Exception as e:
        # traceback.print_exc()
        print(colored("error: failed to play in vc", "red"))
        return
    
    if vc != None:
        await vc.disconnect()

    await asyncio.sleep(1)
    await bot.change_presence(activity=discord.Game(name="?help for commands"))
    






@bot.command()
async def talk(ctx):  
    global isProcessing
    global stop_talking

    print("recording")
    voice = ctx.author.voice

    if not voice:
        await ctx.send("You aren't in a voice channel!")

    vc = await voice.channel.connect()  # Connect to the voice channel the author is in.
    connections.update({ctx.guild.id: vc})  # Updating the cache with the guild and channel.
    await ctx.send("Started recording! *a response will be generated after you stop talking*")
    stop_talking = False
    while stop_talking == False:
        if isProcessing == False:
            vc.start_recording(
                discord.sinks.WaveSink(),  # The sink type to use.
                once_done,  # What to do once done.
                ctx.channel  # The channel to disconnect from.
            )
            print(colored("started recording", "green"))
            await asyncio.sleep(2) 

            vc.stop_recording()
            isProcessing = True
        await asyncio.sleep(1)   

    await ctx.send("Stopped listening! I will now disconnect from the voice channel. Bye! :wave: hello?") 
    await vc.disconnect()  # Disconnect from the voice channel.




async def once_done(sink: discord.sinks, channel: discord.TextChannel, *args):  # Our voice client already passes these in.
    global isProcessing
    recorded_users = [  # A list of recorded users
        f"<@{user_id}>"
        for user_id, audio in sink.audio_data.items()
    ]
    # await sink.vc.disconnect()  # Disconnect from the voice channel.
    files = [discord.File(audio.file, f"{user_id}.{sink.encoding}") for user_id, audio in sink.audio_data.items()]  # List down the files.
    # await channel.send(f"finished recording audio for: {', '.join(recorded_users)}.", files=files)  # Send a message with the accumulated files.
# save file to the disk
    try:
        for user_id, audio in sink.audio_data.items(): # save the audio to the disk
            # print(audio.file)
            user_recording = f"./audio_export/voice_recording/recorded_audio_{user_id}.{sink.encoding}"
            print(f'wav path {user_recording} {os.path.isfile(user_recording)}')
            #convertmp3
            
            full_user_recording = "./audio_export/voice_recording/full_recording.mp3"

            # remove previous version
            try:
                os.remove(user_recording)
            except:
                pass

            # write to file
            with open(user_recording, "wb") as f:
                f.write(audio.file.getbuffer())
                f.close()

            # convert to mp3
            user_recmp3 = f"./audio_export/voice_recording/uncut_recorded_audio_{user_id}.mp3" #convert to mp3
            subprocess.run(["ffmpeg", "-i", user_recording, "-vn", "-ar", "44100", "-y", "-loglevel", "error", "-ac", "2", "-b:a", "192k", user_recmp3]) 

        
            if is_mostly_silence(user_recording): # generate response with fully appended user recording, Only do this if they stopped talking
                print(colored("uwu this file is mostly silence~", "green"))
                await channel.send("recording stopped! processing the audio...")
                audio_file = open(full_user_recording, "rb")
                transcription = client_GPT.audio.transcriptions.create(
                    model="whisper-1",
                    file = audio_file,
                    # prompt="EspiDev, Ai Hoshino, Rikka, Ayanokoji, Ikuyo, Frieren, Joe Biden, Bocchi, Nijika, Ryo, Gen Hoshino, Hitori Gotoh, Nijika Ijichi, Ryo Yamada, Ikuyo Kita, Frieren, Joe Biden, Rikka Takanashi, Kiyotaka Ayanokoji, Kenoi, Seshpenguin, Koitu"
                )
                user_response = str(await turn_informal(transcription.text))

                # whisper
                if user_response == "MBC 뉴스 이덕영입니다.": # no more mbc news glitch
                    user_response = ""
                user = await bot.fetch_user(user_id) # get username
                print(user.display_name + ": " + user_response)
                await channel.send(f'`{user.display_name}: {user_response}`')

                message_buffer.append("user: " + user.display_name + ": " + user_response)

                botResponse = str(await response_gen("§\n".join(message_buffer)))
                print("Response: " + botResponse)
                await channel.send("`" + speaker_name + ": " + botResponse + "`")

                if speaker_language != "english": # translation if not english
                    translation_eng = await translator(botResponse, "english") # translate to english
                    informal_eng = await turn_informal(translation_eng) # turn to texting style
                    await channel.send("`translation: " + informal_eng + "`")


                message_buffer.append(f"Assistant: {speaker_name}: " + str(botResponse))

                #speech
                speech_gen_file = str(speech_gen(botResponse)) # GPT
                rvc_audio_path = str(speech_convert(speech_gen_file)) # RVC
                rvc_audio = AudioSegment.from_wav(rvc_audio_path) # covert mp3 to wav
                rvc_audio.export(speech_convert_file, format="mp3", bitrate="320k")

                print("File: " + speech_convert_file)
                await channel.send(file=discord.File(speech_convert_file))
        
                sink.vc.play(discord.FFmpegPCMAudio(speech_convert_file), after=lambda e: print('Playing speech!', e)) # play the speech
                while sink.vc.is_playing():
                    await asyncio.sleep(1)
                
                try:
                    os.remove(full_user_recording)
                except:
                    pass
                await channel.send("ready for next message!")
            else: # speaking append to full file
                print(colored("nah, there's enough noise here, seshpenguin-san!", "green"))
                if not os.path.isfile(full_user_recording): # create file if not exist
                    print(colored("User Recoridng Path:" + user_recmp3, "green"))
                    print(colored("File not found creating new file", "green"))
                    try:
                        audio_full = AudioSegment.from_file(user_recmp3)
                        audio_full.export(full_user_recording, format="mp3", bitrate="320k")
                    except Exception as e:
                        print(colored("error: failed to create new file", "red"))
                        print(e)
                        traceback.print_exc()   
                else: # append to existing file
                    print(colored("File found appending to existing file", "green"))
                    audio_full = AudioSegment.from_file(full_user_recording)
                    audio_current = AudioSegment.from_file(user_recmp3)
                    audio_full = audio_full + audio_current
                    audio_full.export(full_user_recording, format="mp3")
                    print(colored("File appended", "green"))
                

      
                    
   
                
        isProcessing = False
    except Exception as e:
        print(e)
        traceback.print_exc()
        isProcessing = False

@bot.command()
async def stop(ctx):
    global stop_talking
    stop_talking = True
    await ctx.send("Stopping after this sentence.")

def is_mostly_silence(filename, silence_threshold=-70, nonsilent_chunk_threshold=1):
    # Load the audio file
    subprocess.run(["ffmpeg", "-i", f"{filename}", "-af", "apad=whole_dur=2", f"{filename}.mp3", "-y", "-loglevel", "error"]) # convert to mp3 and pad to 2s
    audio = AudioSegment.from_file(filename+".mp3")

    # Detect nonsilent chunks. Adjust min_silence_len and silence_thresh if needed
    nonsilent_chunks = detect_nonsilent(audio, min_silence_len=500, silence_thresh=silence_threshold)

    # Calculate total duration of nonsilent chunks
    total_nonsilent_duration = sum([end - start for start, end in nonsilent_chunks])

    # Check if the total nonsilent duration is less than the threshold
    is_mostly_silent = total_nonsilent_duration < (0.3 * len(audio)) # if speaking is less than 30% of the audio, then it's mostly silence
    print(total_nonsilent_duration)
    print(len(audio))
    # print(nonsilent_chunk_threshold / 100.0 * len(audio))
    return is_mostly_silent



    
@bot.command()
async def stop_recording(ctx):
    if ctx.guild.id in connections:  # Check if the guild is in the cache.
        vc = connections[ctx.guild.id]
        vc.stop_recording()  # Stop recording, and call the callback (once_done).
        del connections[ctx.guild.id]  # Remove the guild from the cache.
        await ctx.delete()  # And delete.
    else:
        await ctx.send("I am currently not recording here.")  # Respond with this if we aren't recording.


bot.run(DISCORD_TOKEN)
