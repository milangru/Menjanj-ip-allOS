LAN IP MANAGER (CROSS-PLATFORM)
================================

Graficka alatka (Python + Tkinter) za prebacivanje zicne (Ethernet)
mrezne konekcije izmedju automatske DHCP adrese i fiksne IP adrese -
radi na Windows, macOS i Linux.


ZASTO OVA ALATKA
-----------------
Kada cesto menjate mrezu (npr. povremeno pristupate uredjaju na fiksnoj
lokalnoj IP adresi, a inace koristite DHCP), rucno kucanje mreznih
komandi je sporo i podlozno greskama. Ova aplikacija otvara jednostavan
graficki prozor, primenjuje podesavanja preko odgovarajuceg sistemskog
alata za dati OS i restartuje mrezni interfejs da bi se izmene odmah
primenile.


FUNKCIONALNOSTI
----------------
- Radi na Windows (netsh), macOS (networksetup) i Linux (nmcli/ip) -
  automatski prepoznaje OS
- Graficki interfejs (Tkinter) - dolazi ugradjen uz Python, bez
  dodatnih GUI biblioteka
- Prebacivanje izmedju DHCP i fiksne IP jednim klikom
- Podrazumevane (default) vrednosti unapred popunjene u poljima za
  fiksnu IP
- Prikaz stvarne trenutne IP adrese i gateway-a uredjaja, uzivo
  ocitano sa mreznog interfejsa, sa dugmetom za osvezavanje
- Restart mreznog interfejsa posle svake izmene
- Primena podesavanja u pozadinskoj niti (GUI se ne zamrzava)
- Izbor interfejsa iz padajuce liste ako sistem ima vise mreznih
  adaptera


ZAHTEVI
-------
- Python 3 (dolazi predinstaliran na macOS-u i vecini Linux
  distribucija; za Windows preuzeti sa python.org)
- Tkinter modul:
    Windows: dolazi uz standardnu Python instalaciju
    macOS: dolazi uz standardnu Python instalaciju
    Linux (Debian/Ubuntu/Mint): sudo apt install python3-tk
    Linux (Fedora): sudo dnf install python3-tkinter
    Linux (Arch/Manjaro): sudo pacman -S tk
- Administratorske privilegije - obavezno na sva tri sistema, jer
  menjanje IP adrese i restart mreznog adaptera zahtevaju povisena
  ovlascenja


INSTALACIJA
-----------
    git clone https://github.com/<vas-username>/<naziv-repozitorijuma>.git
    cd <naziv-repozitorijuma>


UPOTREBA
--------
Windows (Command Prompt ili PowerShell pokrenut kao Administrator):
    python lan_ip_manager.py

macOS / Linux (terminal):
    sudo python3 lan_ip_manager.py

Ako se na Linuxu GUI ne prikaze zbog $DISPLAY promenljive kad se
koristi sudo, pokrenuti sa:
    sudo -E python3 lan_ip_manager.py

Otvara se prozor sa:
    - padajucom listom za izbor mreznog interfejsa (ako ih ima vise)
    - izborom rezima rada (Fiksna IP / Automatski DHCP)
    - poljima za unos IP adrese, gateway-a i DNS servera (samo za
      fiksni rezim)
    - prikazom stvarne trenutne IP adrese i gateway-a, sa dugmetom
      "Osvezi"
    - dugmetom "Primeni" za primenu izmena


PODESAVANJE PODRAZUMEVANIH VREDNOSTI
-------------------------------------
Podrazumevana fiksna IP adresa, gateway i DNS serveri se menjaju na
vrhu fajla lan_ip_manager.py:

    DEFAULT_IP = "192.168.100.101"
    DEFAULT_PREFIX = "24"
    DEFAULT_GATEWAY = "192.168.100.100"
    DEFAULT_DNS = "8.8.8.8, 1.1.1.1"


NAPOMENE I POZNATA OGRANICENJA
-------------------------------
- Na Windows sistemima ciji je jezik interfejsa drugaciji od
  engleskog, citanje trenutne IP/gateway vrednosti (parsiranje netsh
  izlaza) mozda nece raditi jer su labele lokalizovane - sama primena
  podesavanja (DHCP/fiksna IP) i dalje radi ispravno.
- Podrzane su samo zicne (Ethernet) konekcije, ne Wi-Fi.
- Testirano je uglavnom na Linuxu; Windows i macOS ponasanje treba
  potvrditi na stvarnom sistemu i prijaviti eventualne razlike u
  formatu komandi.


POSTOJI I POSEBNA LINUX (BASH) VERZIJA
----------------------------------------
Za korisnike koji rade iskljucivo na Linuxu sa NetworkManager-om, u
repozitorijumu se nalazi i laksa bash + yad verzija (lan_ip_manager.sh)
sa istim funkcionalnostima, bez potrebe za Python-om.


LICENCA
-------
Slobodno za koriscenje i izmenu. Dodajte licencu po zelji (npr. MIT)
ako planirate javno deljenje repozitorijuma.
