# MP4 → MP3 konverter

Jednostavna desktop aplikacija na hrvatskom jeziku za izdvajanje zvuka iz video datoteka i spremanje u MP3. Podržava obradu više datoteka, povlačenje datoteka u prozor, odabir izlazne mape i bitratea te prikaz napretka.

## Preduvjeti

- Python 3.10 ili noviji za pokretanje iz izvornog koda
- FFmpeg u sistemskom `PATH`-u ili paket `imageio-ffmpeg` (uključen u ovisnosti)

Aplikacija prvo traži FFmpeg u `PATH`-u, a zatim koristi izvršnu datoteku iz paketa `imageio-ffmpeg`.

## Pokretanje iz izvornog koda

U korijenskoj mapi projekta pokrenite:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Na macOS-u ili Linuxu aktivirajte okruženje naredbom `source .venv/bin/activate`.

## Izrada Windows aplikacije

Pokrenite PowerShell u projektu i izvršite:

```powershell
.\build.ps1
```

Ako PowerShell blokira skripte, nakon instalacije ovisnosti pokrenite izravno:

```powershell
.\venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name Mp3Konverter --collect-all imageio_ffmpeg app.py
```

Skripta instalira aplikacijske i PyInstaller ovisnosti u lokalno `venv` okruženje i izrađuje jedinstveni izvršni program `dist\Mp3Konverter.exe`. FFmpeg iz paketa `imageio-ffmpeg` uključuje se u aplikaciju. Za distribuciju kopirajte `.exe` na Windows računalo; prvo pokretanje može potrajati dok se sadržaj aplikacije raspakira.

Trenutno izrađena datoteka nalazi se na `dist\Mp3Konverter.exe` (oko 66 MB).

Nakon objave, preuzmite gotovu aplikaciju s kartice **Releases** u ovom GitHub repozitoriju. Izdanje sadrži `Mp3Konverter.exe`.

## Korištenje

Dodajte video datoteke gumbom **Dodaj datoteke** ili ih povucite u prozor. Odaberite izlaznu mapu po želji, zatim bitrate i kliknite **Pretvori u MP3**. Ako izlazna mapa nije odabrana, MP3 se sprema uz izvornu datoteku. Postojeće datoteke se ne prepisuju; uz naziv se dodaje redni broj.

Podržani ulazni formati: MP4, M4V, MOV, MKV, AVI, WEBM i FLV. Dostupni bitratei: 96, 128, 192, 256 i 320 kbps.

## Struktura projekta

- `app.py` pokreće aplikaciju i provjerava dostupnost FFmpeg-a.
- `frontend.py` sadrži PyQt6 sučelje i pozadinsku nit za konverziju.
- `backend.py` upravlja FFmpeg-om, napretkom i izlaznim putanjama.
- `requirements.txt` navodi pakete potrebne za pokretanje.
- `requirements-build.txt` i `build.ps1` omogućuju izradu Windows `.exe` datoteke.
