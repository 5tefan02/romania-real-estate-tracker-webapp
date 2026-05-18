# modul care trimite mailuri la useri cand apar anunturi noi care le-ar interesa
# se apeleaza la sfarsit, dupa ce s-a normalizat baza de date (din etl/main.py)

import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv
from sqlalchemy import func

from db.connection import SessionLocal
from db.models import (
    Anunt,
    AppUser,
    Compartimentare,
    CriteriiCautare,
    Estate,
    ImagineAnunt,
    IstoricAnunt,
    Judet,
    Localitate,
    NotificareTrimisa,
    TipImobil,
    TipTranzactie,
)


# .env-ul e in radacina proiectului (2 foldere mai sus de fisierul asta)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# Configurari Gmail SMTP
# GMAIL_USER       -> adresa contului Gmail dedicat (ex: evesta.notificari@gmail.com)
# GMAIL_APP_PASSWORD -> "App Password" generata din contul Google (NU parola normala)
#                     -> se genereaza la: https://myaccount.google.com/apppasswords
#                     -> necesita 2FA activat pe cont
# GMAIL_FROM_EMAIL -> ce apare in casuta destinatarului (ex: "Evesta <evesta.notificari@gmail.com>")
GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
GMAIL_FROM_EMAIL = os.getenv("GMAIL_FROM_EMAIL", GMAIL_USER)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587  # port pentru STARTTLS


def _format_price(pret):
    # transforma 150000 in "150.000" - cu punct la mii, cum se scrie la noi
    # (default-ul lui python pune virgula ca in engleza, deci se inlocuieste)
    if pret is None:
        return "-"
    return f"{int(pret):,}".replace(",", ".")


def _format_field(value):
    return value if value not in (None, "", 0) else "-"


def _render_email_html(anunt):
    # HTML-ul mailului e construit direct in cod (cu f-string)
    # CSS-ul e inline pe fiecare element pentru ca asa cer clientii de mail
    # (Gmail/Outlook nu citesc <style> sau fisiere externe)
    # daca anuntul nu are imagine, blocul e gol
    if anunt.get("imagine_url"):
        image_block = (
            f'<img src="{anunt["imagine_url"]}" alt="" '
            'style="width:100%;height:auto;border-radius:8px;display:block;'
            'margin-bottom:20px;" />'
        )
    else:
        image_block = ""

    titlu = f"{_format_field(anunt.get('tip_imobiliar'))} in {_format_field(anunt.get('localitate'))}, {_format_field(anunt.get('judet'))}"

    return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;font-family:Arial,sans-serif;background:#f3f4f6;">
  <div style="max-width:600px;margin:0 auto;padding:32px 24px;background:#ffffff;">
    <h1 style="color:#2563eb;font-size:28px;margin:0 0 4px 0;letter-spacing:-0.5px;">Evesta</h1>
    <p style="color:#6b7280;font-size:14px;margin:0 0 24px 0;">
      Am gasit un anunt nou care se potriveste cu profilul tau.
    </p>

    {image_block}

    <h2 style="color:#1f2937;font-size:20px;margin:0 0 16px 0;">{titlu}</h2>

    <div style="background:#f9fafb;border-radius:8px;padding:20px;margin-bottom:20px;">
      <p style="margin:0 0 4px 0;color:#6b7280;font-size:13px;text-transform:uppercase;letter-spacing:0.5px;">Pret</p>
      <p style="margin:0 0 20px 0;color:#1f2937;font-size:26px;font-weight:bold;">
        {_format_price(anunt.get("pret"))} EUR
      </p>

      <table style="width:100%;font-size:14px;color:#374151;border-collapse:collapse;">
        <tr><td style="padding:6px 0;color:#6b7280;width:140px;">Suprafata</td><td style="padding:6px 0;">{_format_field(anunt.get("suprafata"))} mp</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">Camere</td><td style="padding:6px 0;">{_format_field(anunt.get("camere"))}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">Etaj</td><td style="padding:6px 0;">{_format_field(anunt.get("etaj"))}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">Compartimentare</td><td style="padding:6px 0;">{_format_field(anunt.get("compartimentare"))}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">Tranzactie</td><td style="padding:6px 0;">{_format_field(anunt.get("tip_tranzactie"))}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">An constructie</td><td style="padding:6px 0;">{_format_field(anunt.get("an_constructie"))}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;">Platforma</td><td style="padding:6px 0;">{_format_field(anunt.get("platforma"))}</td></tr>
      </table>
    </div>

    <a href="{anunt.get("url_anunt", "#")}" target="_blank"
       style="display:inline-block;background:#2563eb;color:#ffffff;padding:12px 28px;
              border-radius:6px;text-decoration:none;font-weight:bold;font-size:15px;">
      Vezi anuntul pe {_format_field(anunt.get("platforma"))}
    </a>

    <p style="color:#9ca3af;font-size:12px;margin-top:32px;line-height:1.5;">
      Primesti acest email pentru ca ai un profil de notificari activ in Evesta.
      Poti dezactiva notificarile din pagina ta de profil oricand.
    </p>
  </div>
</body>
</html>
"""


def _send_email(to_email, subject, html):
    # se construieste mesajul ca "multipart" - obligatoriu pentru mailuri cu HTML
    # (clientii de mail vor sa stie ca au de-a face cu HTML, nu text simplu)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_FROM_EMAIL
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html", "utf-8"))

    # conexiune la Gmail SMTP cu STARTTLS (criptare pe port 587)
    # context manager (with...) inchide automat conexiunea la final, chiar daca pica ceva
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)


def _find_matches_for_user(db, user_id, crit):
    # cauta in baza de date anunturile care se potrivesc cu profilul userului
    # impreuna cu datele necesare pentru mail (poza, url, etc)
    # anunturile deja trimise sunt excluse, ca userul sa nu primeasca duplicat

    # pentru fiecare anunt se ia ultima inregistrare din istoric, ca sa se stie
    # daca anuntul mai este activ sau a fost vandut/sters
    latest_istoric_subq = (
        db.query(
            IstoricAnunt.id_anunt.label("id_anunt"),
            func.max(IstoricAnunt.id_istoric).label("latest_id"),
        )
        .group_by(IstoricAnunt.id_anunt)
        .subquery()
    )

    # lista cu id-urile anunturilor trimise deja la user-ul curent
    # -> se exclud din query-ul principal (cu NOT IN)
    already_sent_subq = (
        db.query(NotificareTrimisa.id_anunt)
        .filter(NotificareTrimisa.id_user == user_id)
        .subquery()
    )

    q = (
        db.query(
            Anunt.id_anunt,
            Anunt.pret,
            Anunt.suprafata,
            Anunt.etaj,
            Anunt.an_constructie,
            Anunt.camere,
            Anunt.compartimentare.label("compartimentare_raw"),
            Judet.nume_judet,
            Localitate.nume_localitate,
            TipImobil.nume_tip,
            TipTranzactie.nume_tranzactie,
            Compartimentare.nume_compartimentare,
            Estate.URL_anunt,
            Estate.platforma,
        )
        .join(latest_istoric_subq, Anunt.id_anunt == latest_istoric_subq.c.id_anunt)
        .join(IstoricAnunt, IstoricAnunt.id_istoric == latest_istoric_subq.c.latest_id)
        .join(Localitate, Anunt.id_localitate == Localitate.id_localitate)
        .join(Judet, Localitate.id_judet == Judet.id_judet)
        .outerjoin(TipImobil, Anunt.id_tip_imobiliar == TipImobil.id_tip_imobiliar)
        .outerjoin(TipTranzactie, Anunt.id_tip_tranzactie == TipTranzactie.id_tip_tranzactie)
        .outerjoin(Compartimentare, Anunt.id_compartimentare == Compartimentare.id_compartimentare)
        .outerjoin(Estate, Anunt.id_sursa_raw == Estate.id_raw)
        .filter(IstoricAnunt.status_anunt == "activ")
        .filter(~Anunt.id_anunt.in_(already_sent_subq))
    )

    # se aplica filtrele userului - daca un filtru e null inseamna
    # "orice" pe campul ala, deci nu se adauga in query
    if crit.id_judet is not None:
        q = q.filter(Localitate.id_judet == crit.id_judet)
    if crit.id_localitate is not None:
        q = q.filter(Anunt.id_localitate == crit.id_localitate)
    if crit.id_tip_imobiliar is not None:
        q = q.filter(Anunt.id_tip_imobiliar == crit.id_tip_imobiliar)
    if crit.id_tip_tranzactie is not None:
        q = q.filter(Anunt.id_tip_tranzactie == crit.id_tip_tranzactie)
    if crit.id_compartimentare is not None:
        q = q.filter(Anunt.id_compartimentare == crit.id_compartimentare)
    if crit.pret_min is not None:
        q = q.filter(Anunt.pret >= crit.pret_min)
    if crit.pret_max is not None:
        q = q.filter(Anunt.pret <= crit.pret_max)
    if crit.suprafata_min is not None:
        q = q.filter(Anunt.suprafata >= crit.suprafata_min)
    if crit.suprafata_max is not None:
        q = q.filter(Anunt.suprafata <= crit.suprafata_max)
    if crit.camere is not None:
        # camere e integer pe anunturi (dupa normalizare)
        # anunturile fara camere setate (NULL) nu vor face match, ceea ce e
        # corect: daca userul vrea exact 2 camere si anuntul nu are info,
        # nu i-l trimit.
        q = q.filter(Anunt.camere == crit.camere)

    rows = q.all()

    # se ia o imagine pentru fiecare anunt, ca sa apara in mail
    # in loc de cate un query pe fiecare anunt (ar fi N+1, foarte lent),
    # se face un singur query cu IN(...) si pe urma se grupeaza pe id_anunt
    ids = [r.id_anunt for r in rows]
    imagini_by_anunt = {}
    if ids:
        img_rows = (
            db.query(ImagineAnunt.id_anunt, ImagineAnunt.url_imagine)
            .filter(ImagineAnunt.id_anunt.in_(ids))
            .order_by(ImagineAnunt.id_anunt, ImagineAnunt.ordine.asc().nullslast())
            .all()
        )
        for id_a, url in img_rows:
            # imaginile sunt sortate dupa ordine in query, deci prima e cea principala
            # daca exista deja una pt anuntul asta, celelalte sunt ignorate
            if id_a not in imagini_by_anunt:
                imagini_by_anunt[id_a] = url

    return [
        {
            "id": r.id_anunt,
            "pret": r.pret,
            "suprafata": r.suprafata,
            "etaj": r.etaj,
            "an_constructie": r.an_constructie,
            "judet": r.nume_judet,
            "localitate": r.nume_localitate,
            "tip_imobiliar": r.nume_tip,
            "tip_tranzactie": r.nume_tranzactie,
            "compartimentare": r.nume_compartimentare or r.compartimentare_raw,
            "platforma": r.platforma,
            "camere": r.camere,
            "url_anunt": r.URL_anunt,
            "imagine_url": imagini_by_anunt.get(r.id_anunt),
        }
        for r in rows
    ]


def notify_users():
    # daca nu sunt configurate credentialele Gmail nu se poate trimite nimic
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("[Notificari] GMAIL_USER sau GMAIL_APP_PASSWORD nu sunt setate in .env, sar peste trimitere.")
        return

    session = SessionLocal()
    total_trimise = 0
    total_erori = 0

    try:
        # se iau toti userii cu profil de notificari setat pe activ
        # (cei cu activ=False nu vor sa primeasca mailuri, deci sunt sariti)
        useri = (
            session.query(AppUser, CriteriiCautare)
            .join(CriteriiCautare, AppUser.id == CriteriiCautare.id_user)
            .filter(CriteriiCautare.activ == True)
            .all()
        )

        if not useri:
            print("[Notificari] Niciun user cu profil activ.")
            return

        for user, crit in useri:
            matches = _find_matches_for_user(session, user.id, crit)
            if not matches:
                continue

            print(f"[Notificari] {user.username}: {len(matches)} anunturi noi de trimis.")

            for anunt in matches:
                subject = f"Anunt nou: {anunt.get('tip_imobiliar', 'imobiliar')} in {anunt.get('localitate', '')}"
                html = _render_email_html(anunt)

                try:
                    _send_email(user.email, subject, html)
                    # insert in tabela de notificari trimise abia dupa ce
                    # SMTP a confirmat ca a plecat mailul - altfel daca
                    # trimiterea pica, anuntul ar fi marcat degeaba ca trimis
                    session.add(NotificareTrimisa(
                        id_user=user.id,
                        id_anunt=anunt["id"],
                        data_trimitere=datetime.now(timezone.utc),
                    ))
                    session.commit()
                    total_trimise += 1
                except Exception as e:
                    # daca pica un singur mail, restul trebuie sa mearga in continuare
                    # se afiseaza eroarea si se trece la urmatorul anunt
                    print(f"[Notificari] Eroare la {user.email} pt anunt {anunt['id']}: {e}")
                    session.rollback()
                    total_erori += 1

        print(f"[Notificari] Gata. Trimise: {total_trimise}, erori: {total_erori}")

    finally:
        session.close()
