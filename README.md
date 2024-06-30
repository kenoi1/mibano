# mibano - RVC Discord Bot
### discord bot for texting, chatting, and creating covers with favourite characters using retrieval-based voice conversion.
### you can use it by adding the bot to your server or running locally!
### note: requires openai credits for local running
# How to run locally (quick start)
1. download [RVC-WebUI Project](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI/tree/main)
2. change directory to mibano and create virtual environment
   - `cd ~/mibano`
   - `python3.10 -m venv venv`
   - `source venv/bin/activate`
4. download your version of [pytorch](https://pytorch.org/get-started/locally/)
5. `pip install -r requirements.txt`
6. add environment variables to .env (OPENAI_API_KEY="", DISCORD_TOKEN="", RVC-PATH="*rvc-folder-name*",)
7. `python bot-main.py`
# mibano bot commands:
![mibano](https://cdn.discordapp.com/avatars/125173755071692800/76512edda143a3145f3d154de5295a62.webp?size=160)
## General
**general commands for chatting with kenoibob!**

> *`?help`* - show this message

> *`?speaking`* - show current speaker

> *`?switch <speaker>`* - switch speaker from: {valid_speakers}

> *`?say <text>`* - uses current voice to speak

> *`?ai <text>`* - generates response and speaks it with current voice

## RVC Cover
 **create covers of YouTube videos using voice conversion.**
 
> *`?cover <speaker> <pitch> <start_time> <youtube_url>`* - cover a song using voice conversion

> *`?advcover <speaker> <pitch> <gain> <reverb> <start_time> <youtube_url>`* - ?cover but with more options

 **Parameters**
> **variables for tweaking settings of covers.**

> speaker = {valid_speakers} (string).` Specifies speaker to sing with

> pitch = (integer -72 to ~72).` Specifies pitch in semitones to sing with

> gain = (float, 0 to ~30).` Specifies gain adjust in dB of singing

> reverb = (float 0 to 100).` Specifies reverb % mix

> start_time = (integer 0 to duration-45s).` Specifies start time in seconds of song

## Work in Progress
**broken code, use at own risk.** 
> `?talk` - start listening to your voice channel and talks to you in the current voice ***unfinished***

> `?stop` - stops ?talk ***unfinished***
