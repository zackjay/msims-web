#!/usr/bin/env python3
"""Bina index.html laman MSIMS (EN lalai + BM) daripada templat di bawah.

Sintaks templat:  <tag ...>[[Teks Inggeris||Teks Melayu]]</tag>
                  placeholder="[[English||Melayu]]"
Guna:  python3 build.py <index-asas.html> <folder-keluaran>
Hasil: <keluaran>/site/index.html (EN), site/ms/index.html (BM), robots.txt, sitemap.xml, llms.txt,
       dan <keluaran>/artifact/index.html (satu halaman dengan tukar bahasa di tempat, untuk pratonton).
MSIMS_BETA=0 untuk binaan go-live (boleh diindeks); lalai ialah beta (noindex).
"""
import html as html_mod
import json
import os
import re
import sys

SRC, OUT = sys.argv[1], sys.argv[2].rstrip("/")
old = open(SRC, encoding="utf-8").read()

# ------------------------------------------------------------------ data
SECTORS = [
    ("padi", "Agricultural simulators", "Simulator pertanian",
     "Ministry of Agriculture and Food Security (KPKM), agricultural colleges and institutes, farmers' organisations",
     "Kementerian Pertanian dan Keterjaminan Makanan (KPKM), kolej dan institut pertanian, pertubuhan peladang",
     "Paddy Combine Harvester · SIM-TANI 3-in-1 · Agricultural Drone · VR Farming · VR MyGAP · VR Durian &amp; Strawberry Farm",
     "Jentuai Padi · SIM-TANI 3-dalam-1 · Dron Pertanian · VR Pertanian · VR MyGAP · VR Ladang Durian &amp; Strawberi"),
    ("ikan", "Fisheries simulators", "Simulator perikanan",
     "Department of Fisheries, Fisheries Development Authority of Malaysia (LKIM), fisheries colleges, fishermen's associations",
     "Jabatan Perikanan, Lembaga Kemajuan Ikan Malaysia (LKIM), kolej perikanan, persatuan nelayan",
     "Fishing Vessel · VR Purse Seine Crew · VR Trawl Crew · VR Sayangi Laut Kita",
     "Bot Perikanan · VR Krew Pukat Jerut · VR Krew Pukat Tunda · VR Sayangi Laut Kita"),
    ("sawit", "Oil palm simulators", "Simulator sawit",
     "Ministry of Plantation and Commodities (KPK), oil palm training centres, estate management",
     "Kementerian Perladangan dan Komoditi (KPK), pusat latihan sawit, pengurusan ladang",
     "SIM-SAWIT Haulage: mini tractor and fresh fruit bunch trailer",
     "SIM-SAWIT Angkut: traktor mini dan treler buah tandan segar"),
    ("maritim", "Maritime &amp; port simulators", "Simulator maritim &amp; pelabuhan",
     "Malaysian Maritime Enforcement Agency (APMM), maritime academies, port operators",
     "Agensi Penguatkuasaan Maritim Malaysia (APMM), akademi maritim, pengendali pelabuhan",
     "Patrol Boat Missions · NAKHODA Ship Simulator · STS Crane",
     "Misi Bot Peronda · NAKHODA Simulator Kapal · Kren STS"),
    ("bina", "Construction machinery simulators", "Simulator jentera binaan",
     "Construction industry training centres, contractors, TVET institutions",
     "Pusat latihan industri pembinaan, kontraktor, institusi TVET",
     "Excavator · Backhoe Loader · Forklift",
     "Ekskavator · Jengkaut-Pengaut (backhoe) · Forklif"),
    ("lasak", "Off-road driving simulators", "Simulator pandu lasak",
     "Four-wheel-drive driver training for agencies, plantation companies and the public",
     "Latihan pemanduan pacuan empat roda untuk agensi, syarikat ladang dan orang awam",
     "4WD Off-Road Driving Simulator: village roads, rubber and oil palm estates",
     "Sim Pandu Lasak 4WD: jalan kampung, ladang getah dan sawit"),
]

SIM = ("Simulator", "Simulator")
VR = ("VR module", "Modul VR")
ST = {
    "sedia": ("Ready to supply", "Sedia dibekal"),
    "demo": ("Demo available", "Demo tersedia"),
    "bina": ("In development", "Dalam pembangunan"),
}
F_MB = ("Motion Base", "Motion Base")
F_OFF_MB = ("Offline · Motion Base", "Luar talian · Motion Base")
F_OFF = ("Offline", "Luar talian")
F_Q3 = ("Meta Quest 3", "Meta Quest 3")
F_VR = ("VR", "VR")

# (sektor, jenis, status, nama, huraian, [butir], kaki)
PRODUCTS = [
    ("padi", SIM, "sedia",
     ("Paddy Combine Harvester Simulator", "Simulator Jentuai Padi"),
     ("Harvest, transplant and plough in the paddy field with a combine harvester, rice transplanter and disc-plough tractor. The instrument panel and control tablet change with the selected machine.",
      "Menuai, menanam dan membajak di sawah dengan jentuai, jentanam padi dan traktor bajak piring. Panel instrumen dan tablet kawalan bertukar mengikut jentera yang dipilih."),
     [("Choice of machine and weather", "Pilihan jentera dan cuaca"),
      ("Force-feedback steering that follows the ground surface", "Stereng force-feedback mengikut permukaan tanah")],
     ("Motion Base · Instrument panel", "Motion Base · Panel instrumen")),
    ("padi", SIM, "demo",
     ("SIM-TANI 3-in-1", "SIM-TANI 3-dalam-1"),
     ("Three machines in one program: combine harvester, rice transplanter and rotovator tractor. Work-area coverage is tracked plot by plot.",
      "Tiga jentera dalam satu perisian: jentuai, jentanam padi dan traktor rotovator. Liputan kawasan kerja dijejak petak demi petak."),
     [("Five-criteria scoring", "Pemarkahan lima kriteria"),
      ("Different terrain for each machine", "Rupa bumi berbeza bagi setiap jentera")],
     F_OFF_MB),
    ("padi", SIM, "sedia",
     ("Agricultural Drone Simulator", "Simulator Dron Pertanian"),
     ("From equipment introduction and basic controls to spraying fertiliser and pesticide over paddy fields, Harumanis mango orchards and corn fields.",
      "Dari pengenalan peralatan dan asas kawalan hingga semburan baja dan racun di sawah padi, ladang mangga Harumanis dan ladang jagung."),
     [("9 modules, scored out of 100", "9 modul, markah penuh 100"),
      ("Trainee records and PDF printouts", "Rekod pelatih dan cetakan PDF"),
      ("Real remote controller over USB", "Alat kawalan jauh sebenar melalui USB")],
     F_OFF),
    ("padi", VR, "sedia",
     ("VR Farming", "VR Pertanian"),
     ("Farm tasks done by hand in VR, from planting paddy seedlings to milking a cow, for exhibitions and schools.",
      "Tugasan ladang yang dibuat dengan tangan sendiri dalam VR, daripada menanam anak padi hingga memerah susu lembu, untuk pameran dan sekolah."),
     [], F_VR),
    ("padi", VR, "sedia",
     ("VR MyGAP", "VR MyGAP"),
     ("MyGAP certification good practices explored step by step on a virtual farm.",
      "Amalan baik pensijilan MyGAP diterokai langkah demi langkah di ladang maya."),
     [], F_VR),
    ("padi", VR, "sedia",
     ("VR Durian &amp; Strawberry Farm", "VR Ladang Durian &amp; Strawberi"),
     ("A virtual visit to durian and strawberry farms for exhibitions and learning.",
      "Lawatan ladang durian dan strawberi secara maya untuk pameran dan pembelajaran."),
     [], F_VR),
    ("ikan", SIM, "sedia",
     ("Fishing Vessel Simulator", "Simulator Bot Perikanan"),
     ("Purse seine and trawl operations with six-degree-of-freedom vessel physics, rough weather and night sailing.",
      "Operasi pukat jerut dan pukat tunda dengan fizik bot enam darjah kebebasan, cuaca buruk dan pelayaran malam."),
     [("9 training modules", "9 modul latihan"),
      ("Catch load, engine temperature and fuel consumption", "Beban tangkapan, suhu enjin dan penggunaan bahan api")],
     F_OFF_MB),
    ("ikan", VR, "demo",
     ("VR Purse Seine Crew", "VR Krew Pukat Jerut"),
     ("Players become the crew of a fishing vessel: lowering the fish aggregating device, setting the net and hauling in the catch with hand controllers.",
      "Pemain menjadi krew bot nelayan: menurunkan unjam, melabuh pukat dan menaikkan hasil tangkapan dengan kawalan tangan."),
     [("Designed for children and the public", "Direka untuk kanak-kanak dan orang awam")],
     F_Q3),
    ("ikan", VR, "sedia",
     ("VR Trawl Crew", "VR Krew Pukat Tunda"),
     ("An expo module that puts visitors on the deck of a trawler, complete with winch controls.",
      "Modul ekspo yang membawa pengunjung ke geladak bot pukat tunda, lengkap dengan kawalan winch."),
     [], F_VR),
    ("ikan", VR, "sedia",
     ("VR Sayangi Laut Kita", "VR Sayangi Laut Kita"),
     ("Dive in Malaysia's marine parks as a conservation diver: collecting rubbish and propagating coral against the clock.",
      "Menyelam di taman laut Malaysia sebagai penyelam konservasi: mengutip sampah dan membiak karang dalam had masa."),
     [("Choice of dive sites", "Pilihan tapak selaman"),
      ("Adjustable time limit and target score", "Had masa dan markah boleh dilaras"),
      ("360° seabed video", "Video 360 dasar laut")],
     F_Q3),
    ("sawit", SIM, "demo",
     ("SIM-SAWIT Haulage", "SIM-SAWIT Angkut"),
     ("Hauling fresh fruit bunches with a mini tractor and trailer on an oil palm estate. Modules are structured in line with oil palm mechanisation training.",
      "Pengangkutan buah tandan segar dengan traktor mini dan treler di ladang sawit. Modul dirangka selari dengan latihan mekanisasi ladang sawit."),
     [("5 scored modules, challenge mode and free mode", "5 modul berskor, mod cabaran dan mod bebas"),
      ("Instructor console on a tablet", "Konsol jurulatih di tablet"),
      ("Motion Base follows the ground surface", "Motion Base mengikut permukaan tanah")],
     F_OFF_MB),
    ("maritim", SIM, "demo",
     ("Patrol Boat Mission Simulator", "Simulator Misi Bot Peronda"),
     ("Six short missions inspired by maritime enforcement duties in Malaysian waters, including patrols around the Langkawi islands. Suited to exhibition visitors.",
      "Enam misi pendek berinspirasikan tugas penguatkuasaan maritim di perairan Malaysia, termasuk rondaan pulau-pulau Langkawi. Sesuai untuk pengunjung pameran."),
     [("Steering wheel, throttle lever and gear selector", "Stereng, tuil pecutan dan pemilih gear"),
      ("AAA and Lite graphics modes", "Mod grafik AAA dan Ringan")],
     F_MB),
    ("maritim", SIM, "demo",
     ("NAKHODA Ship Simulator", "NAKHODA Simulator Kapal"),
     ("Ship handling with a ship control console, real-time sea waves and guided control calibration.",
      "Pengendalian kapal dengan konsol kawalan kapal, ombak laut masa nyata dan penentukuran kawalan berpandu."),
     [("Printable competency transcripts", "Transkrip kompetensi bercetak")],
     F_OFF),
    ("maritim", SIM, "sedia",
     ("STS Crane Simulator", "Simulator Kren STS"),
     ("A ship-to-shore crane with container sway physics, sequenced bay plans and weather that affects trolley sway.",
      "Kren ship-to-shore dengan fizik ayunan kontena, pelan bay berturutan dan cuaca yang mempengaruhi ayunan troli."),
     [("Scored on time, sway, accuracy and safety", "Dinilai dari segi masa, ayunan, ketepatan dan keselamatan"),
      ("Instructor mode on a tablet with a 3D spreader view", "Mod jurulatih di tablet dengan paparan 3D spreader"),
      ("CSV and printed reports", "Laporan CSV dan bercetak")],
     F_MB),
    ("bina", SIM, "demo",
     ("Excavator Simulator", "Simulator Ekskavator"),
     ("A crawler excavator from the cab view, with two joystick levers as the left and right consoles.",
      "Jengkaut berkaki ulat dari pandangan kabin, dengan dua tuil joystick sebagai konsol kiri dan kanan."),
     [("Control settings can be changed and saved", "Tetapan kawalan boleh diubah dan disimpan"),
      ("Bucket-to-ground contact detection", "Pengesanan sentuhan timba dengan tanah")],
     ("Dual joystick consoles", "Konsol dwi-joystick")),
    ("bina", SIM, "demo",
     ("Backhoe Loader Simulator", "Simulator Jengkaut-Pengaut"),
     ("A backhoe loader with particle soil physics, working hydraulic rams and an engine start-up sequence before work begins.",
      "Backhoe loader dengan fizik tanah berzarah, ram hidraulik berfungsi dan urutan hidup enjin sebelum kerja bermula."),
     [("ISO and SAE lever patterns", "Corak tuil ISO dan SAE"),
      ("Arm collision warnings", "Amaran perlanggaran lengan"),
      ("Controller screen on a tablet", "Skrin pengawal di tablet")],
     F_MB),
    ("bina", SIM, "demo",
     ("Forklift Simulator", "Simulator Forklif"),
     ("Seven forklift training modules aligned with the requirements of OSHA 1994, DOSH and NIOSH.",
      "Tujuh modul latihan forklif yang diselaraskan dengan keperluan AKKP 1994, JKKP dan NIOSH."),
     [("Warehouse environment with machine sounds", "Persekitaran gudang dengan bunyi jentera")],
     F_OFF),
    ("lasak", SIM, "bina",
     ("4WD Off-Road Driving Simulator", "Sim Pandu Lasak 4WD"),
     ("About 3 km of village road and 3 km of off-road trail through rubber and oil palm estates, to experience four-wheel-drive features.",
      "Kira-kira 3 km jalan kampung dan 3 km laluan lasak merentas ladang getah dan sawit, untuk merasai ciri pacuan empat roda."),
     [("Force-feedback steering, gears and handbrake", "Stereng force-feedback, gear dan brek tangan"),
      ("Puddles and mud", "Lopak air dan lumpur"),
      ("City map planned", "Peta bandar dirancang")],
     F_MB),
]

CLIENTS = [
    "Kolej Pertanian Malaysia",
    "Lembaga Kemajuan Ikan Malaysia (LKIM)",
    "Jabatan Perikanan Malaysia",
    "Institut Penyelidikan dan Kemajuan Pertanian Malaysia (MARDI)",
    "Lembaga Kemajuan Pertanian Kemubu (KADA)",
    "Jabatan Pertanian Negeri Perlis",
    "Lembaga Pertubuhan Peladang (LPP)",
    "Kolej Perikanan Sultan Nazrin Muizzuddin Shah",
    "Persatuan Nelayan Kebangsaan (NEKMAT)",
    "Bahagian Pembangunan Kapasiti Latihan Pertanian (BPKLP)",
    "Industri Makanan dan Asas Tani (IMAT)",
    "Bahagian Pemodenan Pertanian (BPP)",
]

# ------------------------------------------------------------------ gambar
IMAGES = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "images.json")))


def img(name, alt_en, alt_ms, cls="", sizes=""):
    widths = sorted(w for w, _ in IMAGES[name]["out"])
    big = widths[-1]
    small = widths[0]
    attrs = ' class="%s"' % cls if cls else ""
    attrs += ' src="@@R@@assets/img/%s-%d.webp"' % (name, small)
    if len(widths) > 1:
        attrs += ' srcset="%s"' % ", ".join("@@R@@assets/img/%s-%d.webp %dw" % (name, w, w) for w in widths)
        if sizes:
            attrs += ' sizes="%s"' % sizes
    return '<img%s alt="[[%s||%s]]" width="%d" height="%d" loading="lazy" decoding="async">' % (
        attrs, alt_en, alt_ms, big, round(big / 1.5))


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", html_mod.unescape(name).lower()).strip("-")


# gambar kad katalog, dikunci pada nama Inggeris produk
IMG = {
    "Paddy Combine Harvester Simulator": ("jentuai-padi-pameran-ai",
        "Visitors at the MSIMS paddy combine harvester simulator, with paddy stalks in front of the screens",
        "Pengunjung di simulator jentuai padi MSIMS, dengan rumpun padi di hadapan skrin"),
    "Agricultural Drone Simulator": ("dron-kelas-ai",
        "Trainees holding remote controllers watch a drone view over paddy fields on a large screen",
        "Pelatih memegang alat kawalan jauh sambil melihat pandangan dron di atas sawah pada skrin besar"),
    "VR Farming": ("vr-pertanian-set-kepala",
        "Person wearing a VR headset reaching down during a virtual farming task",
        "Pengguna memakai set kepala VR sedang menunduk melakukan tugasan ladang maya"),
    "VR MyGAP": ("vr-mygap-stesen",
        "Hand-washing station on the virtual farm in VR MyGAP",
        "Stesen basuh tangan di ladang maya dalam VR MyGAP"),
    "VR Durian &amp; Strawberry Farm": ("vr-strawberi-petik",
        "VR hand picking a ripe strawberry in a virtual greenhouse",
        "Tangan VR memetik strawberi masak di rumah hijau maya"),
    "Fishing Vessel Simulator": ("bot-perikanan-kemudi-ai",
        "Man at the wheel of the MSIMS fishing vessel simulator facing large sea-view screens",
        "Lelaki mengemudi simulator bot perikanan MSIMS menghadap skrin besar pemandangan laut"),
    "VR Trawl Crew": ("vr-pukat-tunda-geladak",
        "Three crew members in orange coveralls on a trawler deck in VR",
        "Tiga krew berpakaian jingga di geladak bot pukat tunda dalam VR"),
    "VR Sayangi Laut Kita": ("vr-sayangi-laut-karang",
        "Coral fragments on underwater nursery frames beside a blue crate in VR",
        "Serpihan karang pada rangka semaian dasar laut di sebelah bekas biru dalam VR"),
}
PRODUCTS.sort(key=lambda p: p[3][0] not in IMG)  # produk bergambar dahulu; susunan lain kekal

# (fail, tajuk, kapsyen, alt)
SLIDES = [
    ("bot-perikanan-pameran-ai", ("Fishing Vessel Simulator", "Simulator Bot Perikanan"),
     ("A visitor takes the helm at an exhibition booth while others look on.", "Seorang pengunjung mengemudi di reruai pameran sambil diperhatikan orang ramai."),
     ("Man steering the MSIMS fishing vessel simulator at an exhibition, with a crowd watching", "Lelaki mengemudi simulator bot perikanan MSIMS di pameran, diperhatikan orang ramai")),
    ("jentuai-padi-pameran-ai", ("Paddy Combine Harvester Simulator", "Simulator Jentuai Padi"),
     ("Visitors try the harvester controls at a booth dressed with paddy stalks.", "Pengunjung mencuba kawalan jentuai di reruai yang dihias rumpun padi."),
     ("Visitors at the controls of the MSIMS combine harvester simulator at an exhibition", "Pengunjung di kawalan simulator jentuai MSIMS di sebuah pameran")),
    ("vr-durian-pavilion-ai", ("VR Durian Experience", "Pengalaman VR Durian"),
     ("A visitor explores the virtual durian orchard at a Malaysia pavilion.", "Seorang pengunjung meneroka dusun durian maya di pavilion Malaysia."),
     ("Visitor wearing a VR headset at the Virtual Durian Experience booth in a Malaysia pavilion", "Pengunjung memakai set kepala VR di reruai Virtual Durian Experience dalam pavilion Malaysia")),
    ("vr-sayangi-laut-penyu", ("VR Sayangi Laut Kita", "VR Sayangi Laut Kita"),
     ("Swimming beside a sea turtle over a virtual coral reef.", "Berenang di sisi penyu di atas terumbu karang maya."),
     ("Sea turtle swimming over a coral reef, seen through VR diver gloves", "Penyu berenang di atas terumbu karang, dilihat melalui sarung tangan penyelam VR")),
    ("vr-pukat-tunda-krew", ("VR Trawl Crew", "VR Krew Pukat Tunda"),
     ("Crew members sort the catch on the deck of a trawler.", "Krew mengasingkan hasil tangkapan di geladak bot pukat tunda."),
     ("Four crew members in orange coveralls around a sorting table on a trawler deck in VR", "Empat krew berpakaian jingga mengelilingi meja pengasingan di geladak bot pukat tunda dalam VR")),
    ("dron-pelatih", ("Agricultural Drone Simulator", "Simulator Dron Pertanian"),
     ("A trainee at the drone simulator station, with a real remote controller on the desk.", "Seorang pelatih di stesen simulator dron, dengan alat kawalan jauh sebenar di atas meja."),
     ("Trainee seated at the MSIMS crop drone simulator with a remote controller", "Pelatih duduk di simulator dron tanaman MSIMS dengan alat kawalan jauh")),
    ("vr-durian-belah", ("VR Durian &amp; Strawberry Farm", "VR Ladang Durian &amp; Strawberi"),
     ("Opening a durian by hand in the virtual orchard.", "Membelah durian dengan tangan di dusun maya."),
     ("Durians on a wooden table being opened with a knife in VR", "Durian di atas meja kayu sedang dibelah dengan pisau dalam VR")),
    ("vr-mygap-stesen", ("VR MyGAP", "VR MyGAP"),
     ("A hand-washing station on the virtual farm, part of good agricultural practice.", "Stesen basuh tangan di ladang maya, sebahagian amalan pertanian baik."),
     ("Hand-washing station with an instruction poster on the virtual farm in VR MyGAP", "Stesen basuh tangan dengan poster arahan di ladang maya dalam VR MyGAP")),
]

_slides = "\n".join('''      <figure class="slide%s">
        <div class="ph">%s</div>
        <figcaption><span class="n">%02d / %02d</span><h3>[[%s||%s]]</h3><p>[[%s||%s]]</p></figcaption>
      </figure>''' % (" on" if n == 0 else "", img(f, alt[0], alt[1], sizes="(max-width:820px) 100vw, 680px"),
                      n + 1, len(SLIDES), t[0], t[1], c[0], c[1])
                    for n, (f, t, c, alt) in enumerate(SLIDES))
_dots = "".join('<button type="button" aria-label="%d" aria-current="%s"></button>' % (n + 1, "true" if n == 0 else "false")
                for n in range(len(SLIDES)))
SLIDES_SECTION = '''<section id="lapangan">
  <div class="wrap">
    <div class="head">
      <p class="eyebrow">[[In the field||Di lapangan]]</p>
      <h2>[[Simulators at work.||Simulator sedang digunakan.]]</h2>
      <p class="sub">[[Exhibition floors, training rooms and scenes from inside the VR modules.||Lantai pameran, bilik latihan dan babak dari dalam modul VR.]]</p>
    </div>
    <div class="slides" id="slides" role="region" aria-roledescription="carousel" aria-label="[[Photos of MSIMS simulators in use||Gambar simulator MSIMS sedang digunakan]]" tabindex="0">
%s
      <div class="sctl"><button type="button" class="arrow prev" aria-label="[[Previous slide||Slaid sebelumnya]]">&#8592;</button><button type="button" class="arrow next" aria-label="[[Next slide||Slaid seterusnya]]">&#8594;</button><div class="dots">%s</div></div>
    </div>
  </div>
</section>''' % (_slides, _dots)

RIG_FIGURE = '''<figure>%s<figcaption>[[The combine harvester simulator cab: seat, steering wheel, joysticks and screens.||Kabin simulator jentuai: kerusi, stereng, tuil joystick dan skrin.]]</figcaption></figure>''' % img(
    "jentuai-padi-rig",
    "Yellow-framed MSIMS combine harvester simulator cab with seat, steering wheel, joysticks and screens",
    "Kabin simulator jentuai MSIMS berangka kuning dengan kerusi, stereng, tuil joystick dan skrin")

# soalan lazim: (soalan, jawapan), setiap satu (EN, BM). Dipaparkan pada laman dan dalam data berstruktur.
FAQ = [
    (("What does MSIMS do?", "Apakah yang MSIMS lakukan?"),
     ("MSIMS develops training simulators and VR modules in Malaysia. It supplies complete systems, rents units for exhibitions and builds custom simulators for an organisation's own machinery and curriculum.",
      "MSIMS membangunkan simulator latihan dan modul VR di Malaysia. Ia membekalkan sistem lengkap, menyewakan unit untuk pameran dan membina simulator tersuai mengikut jentera dan kurikulum sesebuah organisasi.")),
    (("Which simulators does MSIMS make?", "Simulator apakah yang MSIMS hasilkan?"),
     ("The catalogue includes a paddy combine harvester simulator, an agricultural drone simulator, a fishing vessel simulator, an oil palm haulage simulator, a patrol boat mission simulator, a ship-to-shore (STS) crane simulator, excavator, backhoe loader and forklift simulators, a 4WD off-road driving simulator, and VR modules for farming, MyGAP, fisheries and marine conservation.",
      "Katalog merangkumi simulator jentuai padi, simulator dron pertanian, simulator bot perikanan, simulator angkut sawit, simulator misi bot peronda, simulator kren ship-to-shore (STS), simulator ekskavator, jengkaut-pengaut dan forklif, simulator pandu lasak 4WD, serta modul VR untuk pertanian, MyGAP, perikanan dan konservasi laut.")),
    (("Can the simulators run without an internet connection?", "Bolehkah simulator berjalan tanpa internet?"),
     ("Yes. MSIMS simulators run offline in labs, colleges and exhibition halls, and each licence is locked to its device.",
      "Ya. Simulator MSIMS berjalan luar talian di makmal, kolej dan tapak pameran, dan setiap lesen dikunci pada perantinya.")),
    (("Can MSIMS simulators be rented for an exhibition?", "Bolehkah simulator MSIMS disewa untuk pameran?"),
     ("Yes. Simulator and VR units can be rented for expos, open days and outreach programmes, with short scenarios suited to the public.",
      "Ya. Unit simulator dan VR boleh disewa untuk ekspo, hari terbuka dan program jangkauan, dengan senario pendek yang sesuai untuk orang awam.")),
    (("Can MSIMS build a simulator for our own machinery?", "Bolehkah MSIMS membina simulator untuk jentera kami sendiri?"),
     ("Yes. MSIMS builds custom simulators and VR modules around an organisation's machinery, curriculum and working procedures.",
      "Ya. MSIMS membina simulator dan modul VR tersuai mengikut jentera, kurikulum dan prosedur kerja sesebuah organisasi.")),
    (("How do I request a demo or a quotation?", "Bagaimana hendak meminta demo atau sebut harga?"),
     ("Use the enquiry form on this page, email sales@msims.tech or call +6017-22 33 070. MSIMS is at No. 17A, Jalan SG 8/7, Taman Sri Gombak, 68100 Batu Caves, Selangor.",
      "Gunakan borang pertanyaan di laman ini, e-mel sales@msims.tech atau hubungi +6017-22 33 070. MSIMS terletak di No. 17A, Jalan SG 8/7, Taman Sri Gombak, 68100 Batu Caves, Selangor.")),
]
_faq = "\n".join("      <div><h3>[[%s||%s]]</h3><p>[[%s||%s]]</p></div>" % (q[0], q[1], a[0], a[1]) for q, a in FAQ)
ABOUT_SECTION = '''<section id="soalan">
  <div class="wrap">
    <div class="head">
      <p class="eyebrow">[[About MSIMS||Tentang MSIMS]]</p>
      <h2>[[A Malaysian simulator developer.||Pembangun simulator Malaysia.]]</h2>
    </div>
    <p class="about-lede">[[MSIMS (Motion and Simulation System) is a simulator and VR developer based in Batu Caves, Selangor, Malaysia. The company designs and builds training simulators end to end: the software, the control hardware and the Motion Base. Its simulators and VR modules cover agriculture, fisheries, oil palm, maritime and port operations, construction machinery and off-road driving, and are used by Malaysian government agencies and training institutions.||MSIMS (Motion and Simulation System) ialah pembangun simulator dan VR yang berpangkalan di Batu Caves, Selangor, Malaysia. Syarikat ini mereka bentuk dan membina simulator latihan secara menyeluruh: perisian, perkakasan kawalan dan Motion Base. Simulator dan modul VR MSIMS merangkumi pertanian, perikanan, sawit, operasi maritim dan pelabuhan, jentera binaan dan pandu lasak, dan digunakan oleh agensi kerajaan serta institusi latihan di Malaysia.]]</p>
    <p class="faq-title">[[Frequently asked questions||Soalan lazim]]</p>
    <div class="faq">
%s
    </div>
  </div>
</section>''' % _faq


count = {k: sum(1 for p in PRODUCTS if p[0] == k) for k in [s[0] for s in SECTORS]}


def plural(n):
    return "simulator" if n == 1 else "simulators"


sector_rows = "\n".join(f'''    <div class="srow" data-s="{k}">
      <h3>[[{en}||{ms}]]</h3>
      <p class="who">[[<span class="lbl">Built for the needs of</span>{who_en}||<span class="lbl">Dibina untuk keperluan</span>{who_ms}]]</p>
      <p class="what">[[<span class="lbl">Simulators</span>{what_en}||<span class="lbl">Simulator</span>{what_ms}]]</p>
      <button class="btn ghost small" data-go="{k}">[[View {count[k]} {plural(count[k])}||Lihat {count[k]} simulator]]</button>
    </div>''' for k, en, ms, who_en, who_ms, what_en, what_ms in SECTORS)


def card(p):
    s, kind, st, name, desc, items, foot = p
    pic = ""
    if name[0] in IMG:
        f, a_en, a_ms = IMG[name[0]]
        pic = "\n        " + img(f, a_en, a_ms, cls="thumb", sizes="(max-width:640px) 100vw, 400px")
    ul = ""
    if items:
        ul = "\n        <ul>" + "".join(f"<li>[[{a}||{b}]]</li>" for a, b in items) + "</ul>"
    return f'''      <article class="prod" data-s="{s}" id="{slug(name[0])}">{pic}
        <header><span class="tag">[[{kind[0]}||{kind[1]}]]</span><span class="st st-{st}">[[{ST[st][0]}||{ST[st][1]}]]</span></header>
        <h3>[[{name[0]}||{name[1]}]]</h3>
        <p>[[{desc[0]}||{desc[1]}]]</p>{ul}
        <footer>[[{foot[0]}||{foot[1]}]]</footer>
      </article>'''


cards = "\n\n".join(card(p) for p in PRODUCTS)
clients = "\n".join(f"      <li>{c}</li>" for c in CLIENTS)

filters = "\n".join(
    f'      <button aria-pressed="false" data-f="{k}" data-s="{k}"><span>[[{en}||{ms}]]</span><span class="n">{count[k]}</span></button>'
    for k, en, ms in [("padi", "Agriculture", "Pertanian"), ("ikan", "Fisheries", "Perikanan"),
                      ("sawit", "Oil palm", "Sawit"), ("maritim", "Maritime", "Maritim"),
                      ("bina", "Construction", "Binaan"), ("lasak", "Off-road", "Pandu lasak")])

# ------------------------------------------------------------------ badan
BODY = f'''<body>

<div class="beta"><div class="wrap">[[<b>BETA VERSION</b> · for review. The official site stays at msims.tech until this version is approved.||<b>VERSI BETA</b> · untuk semakan. Laman rasmi semasa kekal di msims.tech sehingga versi ini diluluskan.]]</div></div>

<header class="top">
  <div class="wrap">
    <a class="brand" href="#atas" aria-label="MSIMS, back to top"><img src="@@R@@assets/msims-logo-putih.svg" alt="MSIMS, Motion and Simulation System" width="204" height="60"></a>
    <nav aria-label="Main">
      <a href="#sektor">[[Sectors||Sektor]]</a>
      <a href="#platform">[[Platform||Platform]]</a>
      <a href="#produk">[[Simulators||Simulator]]</a>
      <a href="#khidmat">[[Services||Perkhidmatan]]</a>
      <a href="#klien">[[Clients||Klien]]</a>
      <a href="#soalan">[[FAQ||Soalan lazim]]</a>
    </nav>
    <div class="lang" role="group" aria-label="Language / Bahasa">
      @@LANGSW@@
    </div>
    <a class="btn small" href="#hubungi">[[Request a demo||Minta demo]]</a>
  </div>
</header>

<main id="atas">

<div class="hero">
  <div class="wrap">
    <div class="hero-grid">
      <div>
        <p class="eyebrow">[[Simulator system developer · Batu Caves, Selangor||Pembangun sistem simulator · Batu Caves, Selangor]]</p>
        <h1>[[Malaysian-built training simulators for <em>farm, sea and construction site.</em>||Simulator latihan buatan Malaysia untuk <em>ladang, laut dan tapak bina.</em>]]</h1>
        <p class="lede">[[MSIMS designs and builds complete simulator and VR systems: software, control hardware and Motion Base. Trainees learn to operate combine harvesters, fishing vessels, oil palm tractors, patrol boats, excavators and four-wheel drives in Malaysian environments, with no risk to people or machinery.||MSIMS mereka bentuk dan membina sistem simulator dan VR secara menyeluruh: perisian, perkakasan kawalan dan Motion Base. Pelatih belajar mengendali jentuai padi, bot nelayan, traktor sawit, bot peronda, jengkaut dan pacuan empat roda dalam persekitaran Malaysia, tanpa risiko kepada orang atau jentera.]]</p>
        <div class="cta">
          <a class="btn" href="#hubungi">[[Request a demo||Minta demo]]</a>
          <a class="btn ghost" href="#produk">[[See all simulators||Lihat semua simulator]]</a>
        </div>
      </div>

      <div class="console" id="console">
        <div class="console-top"><span class="lamp"></span><span>[[Simulation console||Konsol simulasi]]</span><span class="note">[[illustrative animation||animasi ilustrasi]]</span></div>
        <div class="tabs" role="tablist" aria-label="Scenario">
          <button role="tab" aria-selected="true" data-k="padi">[[Paddy||Padi]]</button>
          <button role="tab" aria-selected="false" data-k="ikan">[[Fisheries||Perikanan]]</button>
          <button role="tab" aria-selected="false" data-k="sawit">[[Oil palm||Sawit]]</button>
          <button role="tab" aria-selected="false" data-k="maritim">[[Maritime||Maritim]]</button>
          <button role="tab" aria-selected="false" data-k="bina">[[Construction||Binaan]]</button>
          <button role="tab" aria-selected="false" data-k="lasak">[[Off-road||Lasak]]</button>
        </div>
        <div class="view">
          <canvas id="sim" role="img" aria-label="Wireframe terrain moving with the selected scenario"></canvas>
          <div class="hud l"><span>[[Scenario||Senario]]</span><b id="hud-scn">Paddy field</b></div>
          <div class="hud r"><span>[[Simulator||Simulator]]</span><b id="hud-prod">Combine Harvester</b></div>
        </div>
        <dl class="readouts" aria-label="Motion Base">
          <div><dt>Pitch</dt><dd><span id="r-pitch">0.0</span><small>°</small></dd></div>
          <div><dt>Roll</dt><dd><span id="r-roll">0.0</span><small>°</small></dd></div>
          <div><dt>Heave</dt><dd><span id="r-heave">0</span><small>cm</small></dd></div>
          <div><dt>[[Speed||Laju]]</dt><dd><span id="r-laju">8</span><small id="r-unit">km/h</small></dd></div>
        </dl>
      </div>
    </div>

    <dl class="facts-strip">
      <div><dt>{len(SECTORS)}</dt><dd>[[sectors: agriculture, fisheries, oil palm, maritime, construction, off-road driving||sektor: pertanian, perikanan, sawit, maritim, binaan, pandu lasak]]</dd></div>
      <div><dt>{len(PRODUCTS)}</dt><dd>[[simulators and VR modules in the catalogue||simulator dan modul VR dalam katalog]]</dd></div>
      <div><dt>{len(CLIENTS)}</dt><dd>[[agencies and institutions as clients||agensi dan institusi sebagai klien]]</dd></div>
      <div><dt>BM</dt><dd>[[interface, instructions and reports in Bahasa Melayu||antara muka, arahan dan laporan dalam Bahasa Melayu]]</dd></div>
    </dl>
  </div>
</div>

<div class="wrap"><div class="ruler" aria-hidden="true"></div></div>

{SLIDES_SECTION}

<section id="sektor">
  <div class="wrap">
    <div class="head">
      <p class="eyebrow">[[Sectors||Sektor]]</p>
      <h2>[[Six sectors, one developer.||Enam sektor, satu pembangun.]]</h2>
      <p class="sub">[[Every simulator is built around the machinery, waters and working procedures found in Malaysia, not adapted from foreign software.||Setiap simulator dibina mengikut jentera, perairan dan prosedur kerja di Malaysia, bukan diubah suai daripada perisian luar negara.]]</p>
    </div>

{sector_rows}
  </div>
</section>

<section id="platform" class="plat-bg">
  <div class="wrap">
    <div class="plat-top">
    <div class="head">
      <p class="eyebrow">[[Platform||Platform]]</p>
      <h2>[[From code to a seat that moves.||Dari kod hingga kerusi yang bergerak.]]</h2>
      <p class="sub">[[Software and hardware are developed under one roof. As a result, every MSIMS simulator shares the same standards for controls, scoring and maintenance.||Perisian dan perkakasan dibangunkan di bawah satu bumbung. Hasilnya, setiap simulator MSIMS berkongsi piawaian kawalan, pemarkahan dan penyelenggaraan yang sama.]]</p>
    </div>
    {RIG_FIGURE}
    </div>

    <dl class="specs">
      <div><dt>4<small>DOF</small></dt><dd>[[Motion Base that follows the ground surface and waves in the simulation||Motion Base yang bergerak mengikut permukaan tanah dan ombak dalam simulasi]]</dd></div>
      <div><dt>60<small>Hz</small></dt><dd>[[Motion telemetry from software to platform||Telemetri gerakan dari perisian ke pelantar]]</dd></div>
      <div><dt>100</dt><dd>[[Full marks for each training session, scored automatically||Markah penuh bagi setiap sesi latihan, dikira secara automatik]]</dd></div>
      <div><dt>0</dt><dd>[[Internet connections needed during training||Sambungan internet diperlukan semasa latihan]]</dd></div>
    </dl>

    <dl class="caps">
      <div><dt>[[Real control hardware||Perkakasan kawalan sebenar]]</dt><dd>[[Force-feedback steering wheels, dual joystick levers in ISO and SAE patterns, ship consoles, throttle levers and drone remote controllers.||Stereng force-feedback, tuil joystick berkembar corak ISO dan SAE, konsol kapal, tuil pecutan dan alat kawalan jauh dron.]]</dd></div>
      <div><dt>[[Instructor console on a tablet||Konsol jurulatih di tablet]]</dt><dd>[[Instructors launch scenarios, change weather and wind, and monitor trainees from a tablet.||Jurulatih melancarkan senario, menukar cuaca dan angin, serta memantau pelatih dari tablet.]]</dd></div>
      <div><dt>[[Scoring and transcripts||Pemarkahan dan transkrip]]</dt><dd>[[Trainee name and ID records, session reports and printable competency transcripts.||Rekod nama dan ID pelatih, laporan sesi dan transkrip kompetensi yang boleh dicetak.]]</dd></div>
      <div><dt>[[Offline and licensed||Luar talian dan berlesen]]</dt><dd>[[Runs without internet in labs, colleges or exhibition halls. Licences are locked to the device.||Berjalan tanpa internet di makmal, kolej atau tapak pameran. Lesen dikunci pada peranti.]]</dd></div>
      <div><dt>[[VR modules||Modul VR]]</dt><dd>[[VR experiences for Meta Quest 3 headsets, suited to exhibitions and public learning.||Pengalaman VR untuk set kepala Meta Quest 3, sesuai untuk pameran dan pembelajaran awam.]]</dd></div>
      <div><dt>[[Malaysian environments||Persekitaran Malaysia]]</dt><dd>[[Paddy fields, oil palm and rubber estates, Langkawi waters, construction sites and village roads, modelled on how they look locally.||Sawah, ladang sawit dan getah, perairan Langkawi, tapak bina dan jalan kampung dimodelkan mengikut rupa tempatan.]]</dd></div>
    </dl>
  </div>
</section>

<section id="produk">
  <div class="wrap">
    <div class="head">
      <p class="eyebrow">[[Catalogue||Katalog]]</p>
      <h2>[[Simulators and VR modules.||Simulator dan modul VR.]]</h2>
      <p class="sub">[[Filter by sector. Each product's status is shown plainly: some are ready to supply, some can be demonstrated, some are still in development.||Tapis mengikut sektor. Status setiap produk ditunjukkan dengan jujur: ada yang sedia dibekal, ada yang boleh didemo, ada yang masih dibangunkan.]]</p>
    </div>

    <div class="filters" role="group" aria-label="Sector filter">
      <button aria-pressed="true" data-f="semua"><span>[[All||Semua]]</span><span class="n">{len(PRODUCTS)}</span></button>
{filters}
    </div>
    <ul class="legend">
      <li><span class="st st-sedia">[[Ready to supply||Sedia dibekal]]</span></li>
      <li><span class="st st-demo">[[Demo available||Demo tersedia]]</span></li>
      <li><span class="st st-bina">[[In development||Dalam pembangunan]]</span></li>
    </ul>

    <div class="prods" id="prods">

{cards}

    </div>
  </div>
</section>

<div class="wrap"><div class="ruler" aria-hidden="true"></div></div>

<section id="khidmat">
  <div class="wrap">
    <div class="head">
      <p class="eyebrow">[[Services||Perkhidmatan]]</p>
      <h2>[[Three ways to work with us.||Tiga cara bekerjasama.]]</h2>
    </div>
    <div class="svc">
      <div><h3>[[System sales||Jualan sistem]]</h3><p>[[Complete simulator and VR systems: software, PC, displays, controls and Motion Base, installed and tested at your premises.||Sistem simulator dan VR lengkap: perisian, PC, paparan, kawalan dan Motion Base, dipasang dan diuji di premis anda.]]</p></div>
      <div><h3>[[Exhibition rental||Sewaan pameran]]</h3><p>[[Simulator and VR units for expos, open days and outreach programmes, with short scenarios suited to the public.||Unit simulator dan VR untuk ekspo, hari terbuka dan program jangkauan, dengan senario pendek yang sesuai untuk orang awam.]]</p></div>
      <div><h3>[[Custom development||Pembangunan tersuai]]</h3><p>[[New simulators or VR modules built around your organisation's machinery, curriculum and working procedures.||Simulator atau modul VR baharu mengikut jentera, kurikulum dan prosedur kerja organisasi anda.]]</p></div>
    </div>
  </div>
</section>

<section id="klien" class="plat-bg">
  <div class="wrap">
    <div class="head">
      <p class="eyebrow">[[Our clients||Klien kami]]</p>
      <h2>[[Trusted by the nation's agriculture and fisheries agencies.||Dipercayai agensi pertanian dan perikanan negara.]]</h2>
    </div>
    <ul class="klien">
{clients}
    </ul>
  </div>
</section>

{ABOUT_SECTION}

<section id="hubungi">
  <div class="wrap">
    <div class="contact">
      <div>
        <p class="eyebrow">[[Contact us||Hubungi kami]]</p>
        <h2 style="margin-top:14px">[[Request a demo or a quotation.||Minta demo atau sebut harga.]]</h2>
        <address>
          <div><span class="lbl">[[Headquarters||Ibu pejabat]]</span>MSIMS TECH SERVICES<br>No. 17A, Jalan SG 8/7, Taman Sri Gombak,<br>68100 Batu Caves, Selangor, Malaysia</div>
          <div><span class="lbl">[[Email||E-mel]]</span><a href="mailto:sales@msims.tech">sales@msims.tech</a></div>
          <div><span class="lbl">[[Phone||Telefon]]</span><a href="tel:+60172233070">+6017-22 33 070</a></div>
        </address>
      </div>

      <form id="tanya" method="post" action="@@R@@send.php" novalidate>
        <div class="row2">
          <label for="f-nama"><span>[[Your name||Nama anda]]</span>
            <input id="f-nama" name="name" type="text" autocomplete="name" maxlength="100" required>
          </label>
          <label for="f-org"><span>[[Organisation||Organisasi]]</span>
            <input id="f-org" name="org" type="text" autocomplete="organization" maxlength="140" placeholder="[[e.g. Agricultural College||cth. Kolej Pertanian]]">
          </label>
        </div>
        <div class="row2">
          <label for="f-email"><span>[[Email||E-mel]]</span>
            <input id="f-email" name="email" type="email" autocomplete="email" maxlength="160" required>
          </label>
          <label for="f-tel"><span>[[Phone (optional)||Telefon (pilihan)]]</span>
            <input id="f-tel" name="phone" type="tel" autocomplete="tel" maxlength="40">
          </label>
        </div>
        <div class="row2">
          <label for="f-sektor"><span>[[Sector||Sektor]]</span>
            <select id="f-sektor" name="sector">
              <option value="Agriculture">[[Agriculture||Pertanian]]</option>
              <option value="Fisheries">[[Fisheries||Perikanan]]</option>
              <option value="Oil palm and commodities">[[Oil palm and commodities||Sawit dan komoditi]]</option>
              <option value="Maritime and ports">[[Maritime and ports||Maritim dan pelabuhan]]</option>
              <option value="Construction">[[Construction||Binaan]]</option>
              <option value="Off-road driving">[[Off-road driving||Pandu lasak]]</option>
            </select>
          </label>
          <label for="f-jenis"><span>[[Enquiry type||Jenis pertanyaan]]</span>
            <select id="f-jenis" name="type">
              <option value="Simulator demo">[[Simulator demo||Demo simulator]]</option>
              <option value="System purchase">[[System purchase||Pembelian sistem]]</option>
              <option value="Exhibition rental">[[Exhibition rental||Sewaan untuk pameran]]</option>
              <option value="Custom software development">[[Custom software development||Pembangunan perisian tersuai]]</option>
            </select>
          </label>
        </div>
        <label for="f-nota"><span>[[Message||Mesej]]</span>
          <textarea id="f-nota" name="message" maxlength="3000" placeholder="[[Machinery, number of trainees, programme dates and so on||Jentera, bilangan pelatih, tarikh program dan sebagainya]]"></textarea>
        </label>
        <div class="form-actions">
          <button class="btn" type="submit" id="f-send">[[Send enquiry||Hantar pertanyaan]]</button>
          <span id="f-status" role="status" aria-live="polite"></span>
        </div>
        <p class="hint">[[Your enquiry goes straight to the MSIMS team by email. We reply to the address you give.||Pertanyaan anda dihantar terus kepada pasukan MSIMS melalui e-mel. Kami membalas ke alamat yang anda beri.]]</p>
      </form>
    </div>
  </div>
</section>

</main>

<footer class="site">
  <div class="wrap">
    <img src="@@R@@assets/msims-logo-putih.svg" alt="MSIMS, Motion and Simulation System" width="204" height="60">
    <p>[[© 2026 MSIMS Tech Services<br>Simulators and VR built in Malaysia||© 2026 MSIMS Tech Services<br>Simulator dan VR buatan Malaysia]]</p>
  </div>
</footer>
'''

# ------------------------------------------------------------------ terjemah
ATTR_RE = re.compile(r'(alt|placeholder|aria-label)="\[\[(.*?)\|\|(.*?)\]\]"', re.S)
EL_RE = re.compile(r"<([a-z0-9]+)([^<>]*)>\[\[(.*?)\|\|(.*?)\]\]", re.S)


def localise(tpl, lang, inplace):
    """Pilih satu bahasa (laman statik) atau tanda untuk tukar di tempat (pratonton)."""
    ms_map = {}

    def key(v):
        k = "t%d" % (len(ms_map) + 1)
        ms_map[k] = v
        return k

    def attr(m):
        a, en, ms = m.groups()
        if inplace:
            return '%s="%s" data-i-%s="%s"' % (a, en, a, key(ms))
        return '%s="%s"' % (a, ms if lang == "ms" else en)

    def el(m):
        tag, attrs, en, ms = m.groups()
        if inplace:
            return '<%s%s data-i="%s">%s' % (tag, attrs, key(ms), en)
        return "<%s%s>%s" % (tag, attrs, ms if lang == "ms" else en)

    out = EL_RE.sub(el, ATTR_RE.sub(attr, tpl))
    assert "[[" not in out and "]]" not in out and "||" not in out, "templat tidak lengkap"
    return out, ms_map


# ------------------------------------------------------------------ gaya
style = re.search(r"<style>(.*?)</style>", old, re.S).group(1)
style = re.sub(r"\.tbl\{.*?tbody th\{[^}]*\}\n", "", style, flags=re.S)


def sub1(s, a, b):
    assert s.count(a) == 1, (a[:50], s.count(a))
    return s.replace(a, b)


style = sub1(style, ".filters button span{opacity:.7;margin-left:.4em}", ".filters button .n{opacity:.7;margin-left:.4em}")
style = sub1(style, "#f-out{min-height:150px;color:var(--muted);background:var(--panel-2)}\n", "")
style = sub1(style, "@media (max-width:560px){.top nav{display:none}.top .btn{margin-left:auto}}",
             "@media (max-width:1020px){.top nav{display:none}.top .lang{margin-left:auto}}\n@media (max-width:560px){.brand img{height:48px}.top .btn.small{padding:.6em .7em;font-size:.82rem}}\n@media (max-width:440px){.top .btn{display:none}}")
style = sub1(style, ".hud b{display:block;", ".hud span{display:block}\n.hud b{display:block;")
style = sub1(style, "#f-status{font:400 .8rem/1.3 var(--f-mono);color:var(--signal);min-height:1.3em}",
             "#f-status{font:400 .8rem/1.4 var(--f-mono);color:var(--signal);min-height:1.4em}\n#f-status.err{color:#ff9d8c}\nbutton[disabled]{opacity:.6;cursor:progress}")
style = sub1(style, ".hero h1{font-size:clamp(2.5rem,5.4vw,4.75rem);", ".hero h1{font-size:clamp(2.3rem,4.5vw,4.1rem);")
style = sub1(style, ".hero-grid{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,7fr);", ".hero-grid{display:grid;grid-template-columns:minmax(0,6fr) minmax(0,7fr);")
style = sub1(style, """/* logo rasmi (versi gelap). Di kepala hanya tanda kata dipaparkan: bingkai memangkas baris tagline, fail logo tidak diubah. */
.brand{display:block;flex:none;height:36px;overflow:hidden;text-decoration:none}
.brand img{display:block;height:47.7px;width:auto;max-width:none}""", """/* logo rasmi versi putih, penuh bersama tagline */
.brand{display:block;flex:none;text-decoration:none}
.brand img{display:block;height:60px;width:auto}""")
style = sub1(style, "footer.site img{display:block;width:min(240px,60vw);height:auto}", "footer.site img{display:block;height:60px;width:auto}\n@media (max-width:560px){footer.site img{height:48px}}")
style = sub1(style, ".top .wrap{display:flex;align-items:center;gap:20px;min-height:64px}", ".top .wrap{display:flex;align-items:center;gap:20px;min-height:86px}")
style = sub1(style, "section{padding-block:clamp(56px,8vw,104px);scroll-margin-top:70px}", "section{padding-block:clamp(56px,8vw,104px);scroll-margin-top:92px}")
style = sub1(style, "@media (max-width:860px){.top .wrap{gap:10px}.top nav a{padding:.7em .55em}}", "@media (max-width:1180px){.top .wrap{gap:12px}.top nav a{padding:.7em .5em}}")
style += """
/* pemilih bahasa */
.lang{display:flex;flex:none;border:1px solid var(--line);border-radius:2px}
.lang button,.lang a{font:500 .74rem/1 var(--f-mono);letter-spacing:.08em;padding:.62em .7em;background:transparent;border:0;color:var(--muted);cursor:pointer;text-decoration:none}
.lang button:hover,.lang a:hover{color:var(--ink)}
.lang button[aria-pressed="true"],.lang a[aria-current="page"]{background:var(--panel-2);color:var(--ink)}

/* tayangan slaid: gambar di kiri, kapsyen di kanan; slaid bertindan dalam satu sel grid */
.slides{position:relative;display:grid;border:1px solid var(--line);background:var(--panel)}
.slide{grid-area:1/1;margin:0;display:grid;grid-template-columns:minmax(0,7fr) minmax(0,5fr);opacity:0;visibility:hidden;transition:opacity .7s ease,visibility 0s linear .7s}
.slide.on{opacity:1;visibility:visible;transition:opacity .7s ease}
.slide .ph{overflow:hidden;aspect-ratio:3/2;background:#060d22}
.slide img{display:block;width:100%;height:100%;object-fit:cover;transform:scale(1.06);transition:transform 7s ease-out}
.slide.on img{transform:scale(1)}
.slide figcaption{display:flex;flex-direction:column;justify-content:flex-end;gap:10px;padding:clamp(20px,3vw,36px);padding-bottom:84px;min-width:0}
.slide .n{font:500 .74rem/1 var(--f-mono);letter-spacing:.14em;color:var(--amber);font-variant-numeric:tabular-nums}
.slide h3{font-size:clamp(1.6rem,2.6vw,2.3rem)}
.slide p{color:var(--muted);line-height:1.5}
.sctl{position:absolute;right:0;bottom:0;width:41.666%;display:flex;align-items:center;gap:8px;padding:0 clamp(20px,3vw,36px) 24px}
.sctl .arrow{width:40px;height:40px;border:1px solid var(--line);background:transparent;color:var(--ink);cursor:pointer;font:400 1.1rem/1 var(--f-mono);border-radius:2px}
.sctl .arrow:hover{border-color:var(--muted);background:var(--panel-2)}
.dots{display:flex;gap:5px;margin-left:auto}
.dots button{width:20px;height:24px;border:0;padding:0;cursor:pointer;background:linear-gradient(var(--line),var(--line)) center/100% 4px no-repeat}
.dots button[aria-current="true"]{background-image:linear-gradient(var(--amber),var(--amber))}
@media (max-width:820px){
  .slide{grid-template-columns:minmax(0,1fr)}
  .slide figcaption{padding-bottom:14px;min-height:170px;justify-content:flex-start}
  .sctl{position:static;width:auto;padding:0 20px 18px}
}
@media (prefers-reduced-motion:reduce){.slide,.slide.on{transition:none}.slide img{transform:none;transition:none}}

/* gambar pada kad katalog */
.prod .thumb{display:block;width:calc(100% + 40px);max-width:none;height:auto;margin:-20px -20px 6px;aspect-ratio:3/2;object-fit:cover;background:#060d22}

/* platform: tajuk bersama foto rig */
.plat-top{display:grid;grid-template-columns:minmax(0,7fr) minmax(0,5fr);gap:clamp(24px,4vw,56px);align-items:end;margin-bottom:clamp(28px,4vw,48px)}
.plat-top .head{margin-bottom:0}
.plat-top figure{margin:0}
.plat-top img{display:block;width:100%;height:auto;border:1px solid var(--line)}
.plat-top figcaption{margin-top:8px;font-size:.86rem;color:var(--muted);line-height:1.4}
@media (max-width:820px){.plat-top{grid-template-columns:minmax(0,1fr)}}

/* tentang dan soalan lazim */
.about-lede{font-size:1.14rem;line-height:1.6;max-width:72ch}
.faq{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 48px;margin-top:clamp(28px,4vw,44px)}
.faq div{padding:18px 0;border-top:1px solid var(--line)}
.faq h3{font:600 1.08rem/1.35 var(--f-body);text-transform:none;letter-spacing:0}
.faq p{margin-top:6px;color:var(--muted);font-size:.98rem;line-height:1.55}
.faq-title{font:600 1.3rem/1.2 var(--f-display);text-transform:uppercase;letter-spacing:.02em;margin-top:clamp(28px,4vw,44px)}
.faq-title + .faq{margin-top:14px}
@media (max-width:760px){.faq{grid-template-columns:minmax(0,1fr)}}
"""

# ------------------------------------------------------------------ skrip
canvas = re.search(r"(  /\* -+ konsol simulasi \(kanvas\) -+ \*/.*?)\n\}\)\(\);", old, re.S).group(1)
for a, b in [
    ('scn:"Sawah padi",prod:"Jentuai Padi"', 'scn:{en:"Paddy field",ms:"Sawah padi"},prod:{en:"Combine Harvester",ms:"Jentuai Padi"}'),
    ('scn:"Laut pesisir",prod:"Bot Perikanan"', 'scn:{en:"Coastal waters",ms:"Laut pesisir"},prod:{en:"Fishing Vessel",ms:"Bot Perikanan"}'),
    ('scn:"Ladang sawit",prod:"SIM-SAWIT Angkut"', 'scn:{en:"Oil palm estate",ms:"Ladang sawit"},prod:{en:"SIM-SAWIT Haulage",ms:"SIM-SAWIT Angkut"}'),
    ('scn:"Perairan terbuka",prod:"Misi Bot Peronda"', 'scn:{en:"Open waters",ms:"Perairan terbuka"},prod:{en:"Patrol Boat Missions",ms:"Misi Bot Peronda"}'),
    ('scn:"Tapak korekan",prod:"Ekskavator"', 'scn:{en:"Excavation site",ms:"Tapak korekan"},prod:{en:"Excavator",ms:"Ekskavator"}'),
    ('scn:"Laluan lasak",prod:"Pandu Lasak 4WD"', 'scn:{en:"Off-road trail",ms:"Laluan lasak"},prod:{en:"4WD Off-Road",ms:"Pandu Lasak 4WD"}'),
    ('rl.textContent=Math.round(s.v*s.k);ru.textContent=s.unit;', 'rl.textContent=Math.round(s.v*s.k);ru.textContent=s.sea?"knot":(lang==="ms"?"km/j":"km/h");'),
    ('$("hud-scn").textContent=s.scn;$("hud-prod").textContent=s.prod;', 'hud();'),
    ('  function select(k){', '  function hud(){var s=S[cur];$("hud-scn").textContent=s.scn[lang];$("hud-prod").textContent=s.prod[lang]}\n  function select(k){'),
]:
    canvas = sub1(canvas, a, b)
assert canvas.count('unit:"km/j",') == 4 and canvas.count('unit:"knot",') == 2
canvas = canvas.replace('unit:"km/j",', "sea:false,").replace('unit:"knot",', "sea:true,")

I18N_JS = r'''
  /* ---------- pratonton: tukar bahasa di tempat ---------- */
  var MS=__MS__,EN={},ATTRS=["alt","placeholder","aria-label"];
  var tnodes=[].slice.call(document.querySelectorAll("[data-i]"));
  tnodes.forEach(function(n){EN[n.getAttribute("data-i")]=n.innerHTML});
  var anodes=[];
  ATTRS.forEach(function(a){[].forEach.call(document.querySelectorAll("[data-i-"+a+"]"),function(n){var k=n.getAttribute("data-i-"+a);EN[k]=n.getAttribute(a);anodes.push([n,a,k])})});
  function setLang(l,save){
    lang=l==="ms"?"ms":"en";
    document.documentElement.lang=lang;
    var T=lang==="ms"?MS:EN;
    tnodes.forEach(function(n){n.innerHTML=T[n.getAttribute("data-i")]});
    anodes.forEach(function(x){x[0].setAttribute(x[1],T[x[2]])});
    [].forEach.call(document.querySelectorAll(".lang button"),function(b){b.setAttribute("aria-pressed",b.getAttribute("data-lang")===lang?"true":"false")});
    hud();readouts();
    if(lastMsg)say(lastMsg.k,lastMsg.err);
    if(save){try{localStorage.setItem("msims-lang",lang)}catch(e){}}
  }
  [].forEach.call(document.querySelectorAll(".lang button"),function(b){b.addEventListener("click",function(){setLang(b.getAttribute("data-lang"),true)})});
  var saved=null;try{saved=localStorage.getItem("msims-lang")}catch(e){}
  if(saved==="ms")setLang("ms",false);
'''

SCRIPT = r'''(function(){
  "use strict";
  var $=function(id){return document.getElementById(id)};
  var reduce=window.matchMedia&&window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var lang=document.documentElement.lang==="ms"?"ms":"en",lastMsg=null;
  var MSG={
    en:{sending:"Sending…",sent:"Sent. Thank you, we will reply by email.",invalid:"Please enter your name and a valid email address.",rate:"Too many attempts. Please try again later.",fail:"Could not send. Please email sales@msims.tech instead.",preview:"This preview has no mail server. Use the hosted beta link to test the form."},
    ms:{sending:"Menghantar…",sent:"Dihantar. Terima kasih, kami akan membalas melalui e-mel.",invalid:"Sila isi nama dan alamat e-mel yang sah.",rate:"Terlalu banyak cubaan. Sila cuba sebentar lagi.",fail:"Tidak dapat dihantar. Sila e-mel sales@msims.tech.",preview:"Pratonton ini tiada pelayan e-mel. Guna pautan beta Hostinger untuk menguji borang."}
  };

  /* ---------- navigasi dalam laman ---------- */
  document.addEventListener("click",function(e){
    var a=e.target.closest&&e.target.closest('a[href^="#"]');
    if(!a)return;
    var t=document.getElementById(a.getAttribute("href").slice(1));
    if(!t)return;
    e.preventDefault();
    t.scrollIntoView({behavior:reduce?"auto":"smooth",block:"start"});
  });

  /* ---------- tayangan slaid ---------- */
  (function(){
    var box=$("slides");if(!box)return;
    var figs=[].slice.call(box.querySelectorAll(".slide")),dots=[].slice.call(box.querySelectorAll(".dots button"));
    var i=0,timer=0,seen=false,hold=false,x0=null;
    function load(k){var im=figs[(k+figs.length)%figs.length].querySelector("img");if(im&&im.getAttribute("loading")==="lazy")im.setAttribute("loading","eager")}
    function show(k){
      k=(k+figs.length)%figs.length;
      figs[i].classList.remove("on");dots[i].setAttribute("aria-current","false");
      i=k;
      figs[i].classList.add("on");dots[i].setAttribute("aria-current","true");
      load(i+1);
    }
    function halt(){clearInterval(timer);timer=0}
    function play(){halt();if(reduce||hold||!seen||document.hidden)return;timer=setInterval(function(){show(i+1)},5500)}
    box.querySelector(".prev").addEventListener("click",function(){show(i-1);play()});
    box.querySelector(".next").addEventListener("click",function(){show(i+1);play()});
    dots.forEach(function(d,k){d.addEventListener("click",function(){show(k);play()})});
    box.addEventListener("pointerenter",function(e){if(e.pointerType==="mouse"){hold=true;halt()}});
    box.addEventListener("pointerleave",function(){hold=false;play()});
    box.addEventListener("focusin",function(){hold=true;halt()});
    box.addEventListener("focusout",function(){hold=false;play()});
    box.addEventListener("keydown",function(e){if(e.key==="ArrowLeft"){show(i-1)}else if(e.key==="ArrowRight"){show(i+1)}});
    box.addEventListener("touchstart",function(e){x0=e.touches[0].clientX},{passive:true});
    box.addEventListener("touchend",function(e){if(x0===null)return;var dx=e.changedTouches[0].clientX-x0;x0=null;if(Math.abs(dx)>45){show(dx<0?i+1:i-1);play()}},{passive:true});
    if(window.IntersectionObserver){new IntersectionObserver(function(en){seen=en[0].isIntersecting;if(seen)load(i+1);play()},{threshold:.25}).observe(box)}else{seen=true;play()}
    document.addEventListener("visibilitychange",play);
  })();

  /* ---------- katalog: tapis ikut sektor ---------- */
  var prods=[].slice.call(document.querySelectorAll("#prods .prod"));
  var fbtns=[].slice.call(document.querySelectorAll(".filters button"));
  function setFilter(f){
    fbtns.forEach(function(b){b.setAttribute("aria-pressed",b.getAttribute("data-f")===f?"true":"false")});
    prods.forEach(function(p){p.hidden=!(f==="semua"||p.getAttribute("data-s")===f)});
  }
  fbtns.forEach(function(b){b.addEventListener("click",function(){setFilter(b.getAttribute("data-f"))})});
  [].forEach.call(document.querySelectorAll("[data-go]"),function(b){
    b.addEventListener("click",function(){
      setFilter(b.getAttribute("data-go"));
      $("produk").scrollIntoView({behavior:reduce?"auto":"smooth",block:"start"});
    });
  });

  /* ---------- borang pertanyaan: dihantar oleh send.php di pelayan ---------- */
  var form=$("tanya"),stat=$("f-status"),sendBtn=$("f-send"),t0=Date.now();
  var hosted=/(^|\.)msims\.tech$|\.hostingersite\.com$/.test(location.hostname);
  function say(k,err){lastMsg={k:k,err:!!err};stat.textContent=MSG[lang][k];stat.className=err?"err":""}
  form.addEventListener("submit",function(e){
    e.preventDefault();
    var nm=$("f-nama"),em=$("f-email");
    var okMail=/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(em.value.trim());
    if(!nm.value.trim()||!okMail){say("invalid",true);(nm.value.trim()?em:nm).focus();return}
    if(!hosted){say("preview",true);return}
    var fd=new FormData(form);fd.append("lang",lang);fd.append("elapsed",String(Date.now()-t0));
    sendBtn.disabled=true;say("sending");
    fetch(form.getAttribute("action"),{method:"POST",body:fd,headers:{"Accept":"application/json"}})
      .then(function(r){return r.json().then(function(j){return {s:r.status,j:j}})})
      .then(function(x){
        if(x.j&&x.j.ok){say("sent");form.reset()}
        else{say(x.s===429?"rate":(x.s===422?"invalid":"fail"),true)}
      })
      .catch(function(){say("fail",true)})
      .then(function(){sendBtn.disabled=false});
  });

__CANVAS__
__I18N__
})();'''

# ------------------------------------------------------------------ kepala, data berstruktur
BASE = "https://msims.tech"
TODAY = "2026-11-22"
META = {
    "en": {
        "title": "MSIMS | Training Simulator &amp; VR Developer in Malaysia",
        "desc": "MSIMS builds training simulators and VR in Malaysia for agriculture, fisheries, oil palm, maritime, ports, construction and off-road driving. Request a demo.",
        "path": "/", "locale": "en_MY",
    },
    "ms": {
        "title": "MSIMS | Pembangun Simulator Latihan &amp; VR di Malaysia",
        "desc": "MSIMS membina simulator latihan dan VR di Malaysia untuk pertanian, perikanan, sawit, maritim, pelabuhan, binaan dan pandu lasak. Minta demo.",
        "path": "/ms/", "locale": "ms_MY",
    },
}
ABOUT = {
    "en": "MSIMS (Motion and Simulation System) is a simulator and VR developer based in Batu Caves, Selangor, Malaysia. It designs and builds training simulators end to end: software, control hardware and Motion Base.",
    "ms": "MSIMS (Motion and Simulation System) ialah pembangun simulator dan VR yang berpangkalan di Batu Caves, Selangor, Malaysia. Ia mereka bentuk dan membina simulator latihan secara menyeluruh: perisian, perkakasan kawalan dan Motion Base.",
}
KNOWS = {
    "en": ["training simulators", "virtual reality training", "agricultural machinery simulators", "combine harvester simulator",
           "agricultural drone simulator", "fishing vessel simulator", "oil palm mechanisation training", "maritime simulators",
           "ship-to-shore crane simulator", "excavator simulator", "backhoe loader simulator", "forklift simulator",
           "off-road driving simulator", "motion platforms"],
    "ms": ["simulator latihan", "latihan realiti maya", "simulator jentera pertanian", "simulator jentuai padi",
           "simulator dron pertanian", "simulator bot perikanan", "latihan mekanisasi sawit", "simulator maritim",
           "simulator kren STS", "simulator ekskavator", "simulator jengkaut-pengaut", "simulator forklif",
           "simulator pandu lasak", "pelantar gerakan"],
}


def plain(s):
    return html_mod.unescape(re.sub(r"<[^>]+>", "", s))


def jsonld(lang):
    li = 0 if lang == "en" else 1
    url = BASE + META[lang]["path"]
    sector_name = {s[0]: plain(s[1 + li]) for s in SECTORS}
    offers = [{
        "@type": "Offer",
        "itemOffered": {
            "@type": "Service",
            "name": plain(p[3][li]),
            "description": plain(p[4][li]),
            "serviceType": "VR training module" if p[1] is VR else "Training simulator",
            "category": sector_name[p[0]],
            "provider": {"@id": BASE + "/#org"},
        },
    } for p in PRODUCTS]
    graph = [
        {
            "@type": "Organization", "@id": BASE + "/#org",
            "name": "MSIMS", "legalName": "MSIMS Tech Services",
            "alternateName": ["Motion and Simulation System", "MSIMS Tech"],
            "url": BASE + "/", "logo": BASE + "/assets/msims-ikon-256.png", "image": BASE + "/assets/og-msims.jpg",
            "description": ABOUT[lang], "email": "sales@msims.tech", "telephone": "+60172233070",
            "address": {"@type": "PostalAddress", "streetAddress": "No. 17A, Jalan SG 8/7, Taman Sri Gombak",
                        "addressLocality": "Batu Caves", "addressRegion": "Selangor", "postalCode": "68100", "addressCountry": "MY"},
            "areaServed": {"@type": "Country", "name": "Malaysia"},
            "knowsAbout": KNOWS[lang],
            "hasOfferCatalog": {"@type": "OfferCatalog",
                                "name": "Simulators and VR modules" if lang == "en" else "Simulator dan modul VR",
                                "itemListElement": offers},
        },
        {"@type": "WebSite", "@id": BASE + "/#site", "url": BASE + "/", "name": "MSIMS",
         "inLanguage": ["en", "ms"], "publisher": {"@id": BASE + "/#org"}},
        {"@type": "WebPage", "@id": url + "#page", "url": url, "name": plain(META[lang]["title"]),
         "description": META[lang]["desc"], "inLanguage": lang, "isPartOf": {"@id": BASE + "/#site"},
         "about": {"@id": BASE + "/#org"}, "primaryImageOfPage": BASE + "/assets/og-msims.jpg"},
        {"@type": "FAQPage", "@id": url + "#faq", "inLanguage": lang,
         "mainEntity": [{"@type": "Question", "name": plain(q[li]),
                         "acceptedAnswer": {"@type": "Answer", "text": plain(a[li])}} for q, a in FAQ]},
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, indent=1).replace("</", "<\\/")


def head(lang, root, mode, beta):
    m = META[lang]
    robots = "noindex, nofollow" if beta else "index, follow, max-image-preview:large"
    seo = ""
    if mode == "site":
        seo = f'''<meta name="robots" content="{robots}">
<link rel="canonical" href="{BASE}{m["path"]}">
<link rel="alternate" hreflang="en" href="{BASE}/">
<link rel="alternate" hreflang="ms" href="{BASE}/ms/">
<link rel="alternate" hreflang="x-default" href="{BASE}/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="MSIMS">
<meta property="og:title" content="{m["title"]}">
<meta property="og:description" content="{m["desc"]}">
<meta property="og:url" content="{BASE}{m["path"]}">
<meta property="og:image" content="{BASE}/assets/og-msims.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="{m["locale"]}">
<meta property="og:locale:alternate" content="{META["ms" if lang == "en" else "en"]["locale"]}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">
{jsonld(lang)}
</script>
'''
    title = m["title"] if mode == "site" else "Laman MSIMS Beta"
    return f'''<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{m["desc"]}">
<meta name="theme-color" content="#050b1c">
{seo}<link rel="icon" type="image/png" href="{root}assets/msims-ikon-256.png">
<link rel="apple-touch-icon" href="{root}assets/msims-ikon-256.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Saira:wght@400;500;600&family=Saira+Condensed:wght@500;600;700;800&display=swap" rel="stylesheet">
<style>{style}</style>
</head>
'''


def langswitch(lang, mode):
    if mode != "site":
        return ('<button type="button" data-lang="en" aria-pressed="true" title="English">EN</button>'
                '<button type="button" data-lang="ms" aria-pressed="false" title="Bahasa Melayu">BM</button>')
    if lang == "en":
        return ('<a href="./" hreflang="en" lang="en" aria-current="page" title="English">EN</a>'
                '<a href="ms/" hreflang="ms" lang="ms" title="Bahasa Melayu">BM</a>')
    return ('<a href="../" hreflang="en" lang="en" title="English">EN</a>'
            '<a href="./" hreflang="ms" lang="ms" aria-current="page" title="Bahasa Melayu">BM</a>')


def page(lang, mode, beta):
    root = "../" if (mode == "site" and lang == "ms") else ""
    body, ms_map = localise(BODY, lang, inplace=(mode != "site"))
    body = body.replace("@@R@@", root).replace("@@LANGSW@@", langswitch(lang, mode))
    script = SCRIPT.replace("__CANVAS__", canvas)
    if mode == "site":
        script = script.replace("__I18N__", "")
    else:
        script = script.replace("__I18N__", I18N_JS.replace("__MS__", json.dumps(ms_map, ensure_ascii=False).replace("</", "<\\/")))
    out = head(lang, root, mode, beta) + body + "\n<script>\n" + script + "\n</script>\n</body>\n</html>\n"
    assert "@@" not in out
    visible = re.sub(r"<style>.*?</style>|<script>.*?</script>|<!DOCTYPE html>", "", out, flags=re.S) + json.dumps(ms_map, ensure_ascii=False)
    for bad in (r"[Rr]ubri", r"Unreal", r"UE5", r"\bHTML\b", r"Three\.js", r"\bWeb\b"):
        assert not re.search(bad, visible), bad
    return out


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)
    return len(text.encode())


# ------------------------------------------------------------------ keluaran
BETA = os.environ.get("MSIMS_BETA", "1") == "1"
n1 = write(OUT + "/site/index.html", page("en", "site", BETA))
n2 = write(OUT + "/site/ms/index.html", page("ms", "site", BETA))
n3 = write(OUT + "/artifact/index.html", page("en", "artifact", True))

write(OUT + "/site/robots.txt",
      "User-agent: *\nDisallow: /\n" if BETA else
      "User-agent: *\nAllow: /\nDisallow: /send.php\n\nSitemap: %s/sitemap.xml\n" % BASE)

write(OUT + "/site/sitemap.xml", f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <url>
    <loc>{BASE}/</loc>
    <lastmod>{TODAY}</lastmod>
    <xhtml:link rel="alternate" hreflang="en" href="{BASE}/"/>
    <xhtml:link rel="alternate" hreflang="ms" href="{BASE}/ms/"/>
    <xhtml:link rel="alternate" hreflang="x-default" href="{BASE}/"/>
  </url>
  <url>
    <loc>{BASE}/ms/</loc>
    <lastmod>{TODAY}</lastmod>
    <xhtml:link rel="alternate" hreflang="en" href="{BASE}/"/>
    <xhtml:link rel="alternate" hreflang="ms" href="{BASE}/ms/"/>
    <xhtml:link rel="alternate" hreflang="x-default" href="{BASE}/"/>
  </url>
</urlset>
''')

sector_en = {s[0]: plain(s[1]) for s in SECTORS}
llms = ["# MSIMS (Motion and Simulation System)", "",
        "> " + ABOUT["en"] + " Its simulators and VR modules cover agriculture, fisheries, oil palm, maritime and port operations, construction machinery and off-road driving.", "",
        "MSIMS Tech Services, No. 17A, Jalan SG 8/7, Taman Sri Gombak, 68100 Batu Caves, Selangor, Malaysia. Email sales@msims.tech, phone +6017-22 33 070.", "",
        "## Pages", "",
        "- [MSIMS home (English)](%s/): sectors, platform, full simulator catalogue, services, clients, FAQ and enquiry form" % BASE,
        "- [MSIMS laman utama (Bahasa Melayu)](%s/ms/): the same content in Malay" % BASE, ""]
for k in [s[0] for s in SECTORS]:
    llms += ["## " + sector_en[k], ""]
    for p in PRODUCTS:
        if p[0] == k:
            llms.append("- %s (%s; %s): %s" % (plain(p[3][0]), plain(p[1][0]), ST[p[2]][0].lower(), plain(p[4][0])))
    llms.append("")
llms += ["## Services", "",
         "- System sales: complete simulator and VR systems, installed and tested on site",
         "- Exhibition rental: simulator and VR units for expos, open days and outreach programmes",
         "- Custom development: new simulators or VR modules for an organisation's own machinery, curriculum and procedures", "",
         "## Clients", ""] + ["- " + c for c in CLIENTS] + [""]
write(OUT + "/site/llms.txt", "\n".join(llms))

print("ok: en %d bait, ms %d bait, pratonton %d bait, %d produk" % (n1, n2, n3, len(PRODUCTS)))
