# All_In_One_DiscordBot
discord.py의 Cog기능을 이용해서 봇을 만들어보았습니다!

추가 예정인 기능 리스트:
1. LLM모델 이용해서 채팅 기능 만들기
2. 노래기능 만들기
3. 간단한 게임 추가

python 3.10.12

dotenv 1.0.1  
pip install python-dotenv

discord 2.4.0  
pip install -U discord.py

yt-dlp 2024.12.23  
pip install yt-dlp

PyNaCl 1.5.0  
pip install PyNaCl

ffmpeg  
https://www.ffmpeg.org/download.html

yt-dlp -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]" -o './%(title)s.%(ext)s' --cookies-from-browser chrome "유튜브링크"
