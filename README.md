# mibano - RVC Discord Bot
### discord bot for texting, chatting, and creating covers with favourite characters using retrieval-based voice conversion.
### you can use it by adding the bot to your server or running locally!
### note: requires openai credits for local running
# How to run locally (quick start)
1. RVC-WebUI Project
2. pytorch
3. pip -r requirements.txt
'# kenoibob Commands:\n'
    ''
    '## General\n'
    '> **general commands for chatting with kenoibob!**\n'
    '> *`?help`* - show this message\n'
    '> *`?speaking`* - show current speaker\n'
    f'> *`?switch <speaker>`* - switch speaker from: {valid_speakers}\n'
    '> *`?say <text>`* - uses current voice to speak\n'
    '> *`?ai <text>`* - generates response and speaks it with current voice\n'
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
