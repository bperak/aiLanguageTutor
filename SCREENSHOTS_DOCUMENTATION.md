# Dokumentacija Screenshotova - AI Language Tutor
## TheCUC Konferencija, Rovinj, 7. studenog 2025.

---

## 📸 Pregled Screenshotova

Sve screenshotove možete pronaći u `Downloads/` direktoriju s prefiksom imena i timestampom.

---

## 🎯 Korisnički Put (User Journey)

### 1. Landing Stranica
**Screenshot:** `01-landing-page-*.png`

**Opis:**
- Početna stranica aplikacije za neautentificirane korisnike
- Naslov: "Learn languages with your AI tutor"
- Podnaslov: "Personalized, simple, and effective. Start with Japanese today."
- Dva glavna gumba: "Get started" (registracija) i "I already have an account" (prijava)
- Navigacijska traka s opcijama: Login i Sign Up

**Koraci:**
1. Korisnik pristupa aplikaciji na `http://localhost:3000`
2. Vidí landing stranicu s pozivom na akciju

---

### 2. Registracija - Prazna Forma
**Screenshot:** `02-register-page-form-*.png`

**Opis:**
- Registracijska forma s tri polja:
  - Email
  - Username
  - Password
- Gumb "Create account"
- Link "Already have an account? Sign in"

**Koraci:**
1. Korisnik klikne na "Get started" ili "Sign Up"
2. Preusmjeren je na `/register` stranicu
3. Vidí praznu registracijsku formu

---

### 3. Registracija - Ispunjena Forma
**Screenshot:** `03-register-filled-*.png`

**Opis:**
- Registracijska forma s ispunjenim podacima:
  - Email: demo.user@thecuc2025.demo
  - Username: demouser
  - Password: (skriven)

**Koraci:**
1. Korisnik ispunjava podatke za registraciju
2. Forma je spremna za slanje

---

### 4. Nakon Registracije
**Screenshot:** `04-after-registration-*.png`

**Opis:**
- Aplikacija procesira registraciju
- Može se preusmjeriti na login ili direktno na home stranicu

**Napomena:** Ako korisnik već postoji, možda će biti greška ili preusmjerenje na login.

---

### 5. Login Stranica
**Screenshot:** `05-login-page-*.png`

**Opis:**
- Login forma s dva polja:
  - Username (ne email!)
  - Password
- Gumb "Sign in"
- Link "Don't have an account? Create one"

**Koraci:**
1. Korisnik klikne na "Login" ili "I already have an account"
2. Preusmjeren je na `/login` stranicu
3. Vidí login formu

---

### 6. Login - Ispunjena Forma (Password)
**Screenshot:** `06-login-filled-*.png`

**Opis:**
- Login forma s ispunjenim password poljem
- Username polje još prazno

---

### 7. Nakon Pokušaja Prijave
**Screenshot:** `07-after-login-*.png`

**Opis:**
- Aplikacija procesira login zahtjev
- Može pokazati loading stanje ili grešku

---

### 8. Login - Ispunjena Forma (Username + Password)
**Screenshot:** `08-login-filled-username-*.png`

**Opis:**
- Login forma s ispunjenim podacima:
  - Username: demouser
  - Password: (skriven)
- Forma spremna za slanje

---

### 9-10. Home Stranica - Učitavanje
**Screenshot:** `09-home-after-login-*.png`, `10-home-loaded-*.png`

**Opis:**
- Loading stanje nakon uspješne prijave
- Aplikacija učitava podatke korisnika
- Može se preusmjeriti na profile build ako profil nije dovršen

---

### 11. Profile Build Stranica
**Screenshot:** `11-profile-build-page-*.png`

**Opis:**
- **Naslov:** "Build Your Learning Profile"
- **Podnaslov:** "Let's get to know you better so we can create a personalized learning experience."
- **AI Tutor Chat Interface:**
  - Chat prozor s AI tutorom
  - Prva poruka od AI tutora: "Hi there! I'm your AI language tutor..."
  - Polje za unos poruke
  - Gumb "Send"
- **Dodatne opcije:**
  - Gumb "Skip for Now" (preskakanje izrade profila)
  - Gumb "Complete Profile"
- **Personalization Suggestions:**
  - Sugestije za metode učenja
  - Sugestije za kontekst uporabe jezika

**Koraci:**
1. Nakon prijave, korisnik se preusmjeri na `/profile/build`
2. Vidí AI tutor chat interface
3. AI tutor pita korisnika o ciljevima učenja

---

### 12. Home Chat Interface
**Screenshot:** `12-home-chat-interface-*.png`

**Opis:**
- Ako korisnik preskoči profile build, vidi glavni home chat interface
- Chat interface s AI tutorom
- Mogućnost razgovora o učenju japanskog

---

### 13. Home Nakon Preskakanja Profila
**Screenshot:** `13-home-after-skip-*.png`

**Opis:**
- Ako korisnik klikne "Skip for Now", vidí profil build stranicu
- AI tutor chat i dalje dostupan

---

### 14. Profile Build - Poruka Ispunjena
**Screenshot:** `14-profile-build-message-filled-*.png`

**Opis:**
- Korisnik je ispunio poruku u chat polju:
  - "Hi! My name is Demo User. I'm interested in learning Japanese for travel and academic purposes. I have some basic knowledge but want to improve my conversational skills."
- Gumb "Send" je aktivan

**Koraci:**
1. Korisnik odgovara na pitanje AI tutora
2. Unosi informacije o sebi i ciljevima učenja
3. Klikne "Send"

---

### 15. Profile Build - AI Odgovor
**Screenshot:** `15-profile-build-ai-response-*.png`

**Opis:**
- AI tutor odgovara na korisnikovu poruku
- Chat razgovor nastavlja
- AI tutor postavlja dodatna pitanja za personalizaciju

**Koraci:**
1. AI tutor analizira korisnikovu poruku
2. Generira personalizirani odgovor
3. Postavlja dodatna pitanja za personalizaciju profila

---

### 16-17. Dashboard
**Screenshot:** `16-dashboard-*.png`, `17-dashboard-loaded-*.png`

**Opis:**
- Dashboard stranica s učitavanjem
- Nakon učitavanja, možda pokazuje:
  - Statistike napretka
  - Grafove aktivnosti
  - Preporuke za učenje
  - Nedavne aktivnosti

**Napomena:** Dashboard može tražiti dovršen profil prije prikaza.

---

### 18. Grammar Stranica
**Screenshot:** `18-grammar-page-*.png`

**Opis:**
- **Naslov:** "Japanese Grammar Patterns"
- **Funkcionalnosti:**
  - Browse Patterns
  - Learning Paths
  - Recommendations
  - Filters
- **Prikaz obrazaca:**
  - Lista gramatičkih obrazaca s informacijama:
    - Obrazac (npr. "～は～です")
    - Romanizacija (npr. "~ha~desu")
    - Razina udžbenika (npr. "入門(りかい)")
    - Broj sekvence (npr. "#1")
    - Opis
    - Primjer rečenice
    - Klasifikacija (npr. "説明")
    - JFS kategorija (npr. "1　自分と家族")
  - Gumbi "Study This Pattern" i "Quick Study" za svaki obrazac
- **Paginacija:**
  - "Showing 1–20 of 431 patterns"
  - Navigacijski gumbi za stranice

**Koraci:**
1. Korisnik klikne na "Grammar" u navigaciji
2. Vidí listu gramatičkih obrazaca
3. Može pregledavati, filtrirati i studirati obrasce

**Ključni podaci:**
- **431 gramatičkih obrazaca** dostupno za učenje
- Organizirano po razinama udžbenika
- Povezano s JFS kategorijama

---

### 19. Conversations Stranica
**Screenshot:** `19-conversations-page-*.png`

**Opis:**
- **Sekcija Sessions:**
  - Lista sesija razgovora
  - Opcije za svaku sesiju:
    - "Rename"
    - "Delete"
- **Provider Selection:**
  - Opcije: "OpenAI" i "Gemini"
- **Model Selection:**
  - Dropdown za odabir AI modela
- **Pretraga:**
  - "Search sessions" polje
- **Akcije:**
  - "New session" gumb
  - "Export All" gumb
  - "Export TXT" i "Export JSON" opcije
- **Chat Interface:**
  - Chat prozor za razgovor
  - Polje za unos poruke
  - Gumb "Send"
  - Gumb "Save"

**Koraci:**
1. Korisnik klikne na "Conversations" u navigaciji
2. Vidí listu svojih sesija razgovora
3. Može kreirati novu sesiju ili otvoriti postojeću
4. Može odabrati AI provider (OpenAI/Gemini) i model

---

### 20-22. Home Chat Interface - Razgovor s AI Tutorom
**Screenshot:** 
- `20-home-main-chat-*.png` - Glavni chat interface
- `21-home-chat-question-*.png` - Pitanje korisnika
- `22-home-chat-ai-response-*.png` - AI odgovor

**Opis:**
- **Home Chat Interface:**
  - Glavni chat prozor na home stranici
  - Mogućnost razgovora s AI tutorom
  - Real-time streaming AI odgovora
- **Pitanje korisnika:**
  - "Kako mogu naučiti japanski alfabet?"
  - Uneseno u chat polje
- **AI Odgovor:**
  - AI tutor generira personalizirani odgovor
  - Objašnjava japanski alfabet (Hiragana, Katakana, Kanji)
  - Daje konkretne preporuke za učenje

**Koraci:**
1. Korisnik je na home stranici
2. Unosi pitanje u chat polje
3. Klikne "Send"
4. AI tutor generira streaming odgovor
5. Korisnik prima personalizirani odgovor

**Ključne značajke:**
- Real-time streaming AI odgovora
- Personalizirani kontekst
- Interaktivni razgovor o učenju

---

### 23. Knowledge Stranica
**Screenshot:** `23-knowledge-page-*.png`

**Opis:**
- Stranica za pretraživanje i pregled znanja
- Može uključivati:
  - Pretraživanje grafa znanja
  - Pregled čvorova i relacija
  - Analizu sadržaja
  - Integraciju s grafa znanja

---

## 📊 Statistike i Ključni Podaci za Prezentaciju

### Graf Znanja (Neo4j)
- **Ukupno čvorova:** 138,691
- **Ukupno relacija:** 185,817
- **Gramatički obrasci:** 392 (Marugoto kurikulum)
- **Riječi:** 138,153
- **Gramatičke klasifikacije:** 63
- **Marugoto teme:** 55
- **JFS kategorije:** 25
- **Razine udžbenika:** 6

### Tipovi Relacija
- **SYNONYM_OF:** 173,425 relacija
- **SIMILAR_TO:** 4,448 relacija
- **PREREQUISITE_FOR:** 3,654 relacije (učne staze)
- **USES_WORD:** 2,046 relacija (povezanost gramatike i vokabulara)
- **DOMAIN_OF:** 803 relacije
- **BELONGS_TO_LEVEL:** 392 relacije
- **HAS_CLASSIFICATION:** 392 relacije
- **CATEGORIZED_AS:** 392 relacije
- **ANTONYM_OF:** 265 relacija

### Funkcionalnosti Aplikacije
- ✅ Real-time chat s AI tutorom
- ✅ Streaming AI odgovori
- ✅ Personalizirani profil učenja
- ✅ 431 gramatičkih obrazaca za učenje
- ✅ Više sesija razgovora
- ✅ Multi-provider AI (OpenAI + Gemini)
- ✅ Graf znanja integracija
- ✅ Praćenje napretka

---

## 🎯 Preporuke za Prezentaciju

### Redoslijed Screenshotova za Prezentaciju:

1. **Landing Page** (01) - Uvod u aplikaciju
2. **Register** (02-03) - Registracija novog korisnika
3. **Login** (05-08) - Prijava korisnika
4. **Profile Build** (11, 14-15) - Personalizacija profila
5. **Home Chat** (20-22) - Glavni chat interface s AI tutorom
6. **Grammar** (18) - Pregled gramatičkih obrazaca
7. **Conversations** (19) - Upravljanje sesijama razgovora
8. **Knowledge** (23) - Graf znanja integracija

### Ključne Poruke za Naglasiti:

1. **Personalizacija:** AI tutor prilagođava odgovore svakom korisniku
2. **Strukturirano znanje:** 431 gramatičkih obrazaca organiziranih u graf znanja
3. **Real-time interakcija:** Streaming AI odgovori za prirodan razgovor
4. **Multi-provider AI:** Podrška za OpenAI i Gemini
5. **Graf znanja:** 138,691 čvorova i 185,817 relacija za semantičko pretraživanje

---

## 📁 Lokacija Screenshotova

Svi screenshotovi su spremljeni u:
- **Direktorij:** `Downloads/`
- **Format:** PNG
- **Imenovanje:** `{broj}-{naziv}-{timestamp}.png`

Primjer:
- `01-landing-page-2025-11-06T01-08-53-850Z.png`
- `18-grammar-page-2025-11-06T01-12-59-731Z.png`

---

## 🔧 Tehnički Detalji

### Snimljeno s:
- **Playwright MCP Server**
- **Browser:** Chromium (headless=false)
- **URL:** http://localhost:3000
- **Datum:** 6. studenog 2025.

### Testni Korisnik:
- **Email:** demo.user@thecuc2025.demo
- **Username:** demouser
- **Password:** DemoPassword123!

---

## 📝 Napomene

1. **Profile Build:** Ako korisnik ne dovrši profil build, možda neće moći pristupiti svim stranicama
2. **Loading States:** Neke stranice imaju loading stanja koja traju nekoliko sekundi
3. **Real-time Features:** Chat interface koristi streaming za AI odgovore
4. **Multi-language:** Aplikacija trenutno podržava japanski jezik, planirano širenje na druge jezike

---

**Kreirano:** 6. studenog 2025.
**Za:** TheCUC Konferencija, Rovinj, 7. studenog 2025.

