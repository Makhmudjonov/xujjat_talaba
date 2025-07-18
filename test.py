from gtts import gTTS

text = "Juda yaxshi g‘oya — avtomatik qo‘ng‘iroq orqali talabalarga baholarini yetkazish — bu zamonaviy va samarali yondashuv."
tts = gTTS(text,lang="pt")
tts.save("audio_ali.mp3")
