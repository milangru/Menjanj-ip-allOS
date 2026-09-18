# LAN IP Manager (cross-platform)

Grafička alatka (Python + Tkinter) za prebacivanje žične (Ethernet) mrežne konekcije između **automatske DHCP** adrese i **fiksne IP** adrese — radi na **Windows, macOS i Linux**.

## Zašto ova alatka

Kada često menjate mrežu (npr. povremeno pristupate uređaju na fiksnoj lokalnoj IP adresi, a inače koristite DHCP), ručno kucanje mrežnih komandi je sporo i podložno greškama. Ova aplikacija otvara jednostavan grafički prozor, primenjuje podešavanja preko odgovarajućeg sistemskog alata za dati OS i **restartuje mrežni interfejs** da bi se izmene odmah primenile.

## Funkcionalnosti

- Radi na **Windows** (`netsh`), **macOS** (`networksetup`) i **Linux** (`nmcli`/`ip`) — automatski prepoznaje OS
- Grafički interfejs (Tkinter) — dolazi ugrađen uz Python, bez dodatnih GUI biblioteka
- Prebacivanje između **DHCP** i **fiksne IP** jednim klikom
- Podrazumevane (default) vrednosti unapred popunjene u poljima za fiksnu IP
- Prikaz **stvarne trenutne IP adrese i gateway-a** uređaja, uživo očitano sa mrežnog interfejsa, sa dugmetom za osvežavanje
- Restart mrežnog interfejsa posle svake izmene
- Primena podešavanja u pozadinskoj niti (GUI se ne zamrzava)
- Izbor interfejsa iz padajuće liste ako sistem ima više mrežnih adaptera

## Zahtevi

- **Python 3** (dolazi predinstaliran na macOS-u i većini Linux distribucija; za Windows preuzeti sa [python.org](https://www.python.org/downloads/))
- **Tkinter** modul:
  - Windows: dolazi uz standardnu Python instalaciju
  - macOS: dolazi uz standardnu Python instalaciju
  - Linux (Debian/Ubuntu/Mint): `sudo apt install python3-tk`
  - Linux (Fedora): `sudo dnf install python3-tkinter`
  - Linux (Arch/Manjaro): `sudo pacman -S tk`
- **Administratorske privilegije** — obavezno na sva tri sistema, jer menjanje IP adrese i restart mrežnog adaptera zahtevaju povišena ovlašćenja

## Instalacija

```bash
git clone https://github.com/<vas-username>/<naziv-repozitorijuma>.git
cd <naziv-repozitorijuma>
```

## Upotreba

**Windows** (Command Prompt ili PowerShell pokrenut kao Administrator):
```
python lan_ip_manager.py
```

**macOS / Linux** (terminal):
```bash
sudo python3 lan_ip_manager.py
```

Ako se na Linuxu GUI ne prikaže zbog `$DISPLAY` promenljive kad se koristi `sudo`, pokrenuti sa:
```bash
sudo -E python3 lan_ip_manager.py
```

Otvara se prozor sa:
- padajućom listom za izbor mrežnog interfejsa (ako ih ima više)
- izborom režima rada (Fiksna IP / Automatski DHCP)
- poljima za unos IP adrese, gateway-a i DNS servera (samo za fiksni režim)
- prikazom stvarne trenutne IP adrese i gateway-a, sa dugmetom "Osveži"
- dugmetom "Primeni" za primenu izmena

## Podešavanje podrazumevanih vrednosti

Podrazumevana fiksna IP adresa, gateway i DNS serveri se menjaju na vrhu fajla `lan_ip_manager.py`:

```python
DEFAULT_IP = "192.168.100.101"
DEFAULT_PREFIX = "24"
DEFAULT_GATEWAY = "192.168.100.100"
DEFAULT_DNS = "8.8.8.8, 1.1.1.1"
```

## Napomene i poznata ograničenja

- Na Windows sistemima čiji je jezik interfejsa drugačiji od engleskog, čitanje trenutne IP/gateway vrednosti (parsiranje `netsh` izlaza) možda neće raditi jer su labele lokalizovane — sama primena podešavanja (DHCP/fiksna IP) i dalje radi ispravno.
- Podržane su samo žične (Ethernet) konekcije, ne Wi-Fi.
- Testirano je uglavnom na Linuxu; Windows i macOS ponašanje treba potvrditi na stvarnom sistemu i prijaviti eventualne razlike u formatu komandi.

## Postoji i posebna Linux (bash) verzija

Za korisnike koji rade isključivo na Linuxu sa NetworkManager-om, u repozitorijumu se nalazi i lakša `bash + yad` verzija (`lan_ip_manager.sh`) sa istim funkcionalnostima, bez potrebe za Python-om.

## Licenca

Slobodno za korišćenje i izmenu. Dodajte licencu po želji (npr. MIT) ako planirate javno deljenje repozitorijuma.
