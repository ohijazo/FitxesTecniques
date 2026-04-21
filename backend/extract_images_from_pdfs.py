"""
Extreu imatges de certificacio dels PDFs del FTP i les guarda
a uploads/{art_codi}/img/. Actualitza el contingut JSON amb la URL.

Nomes extreu imatges de la pagina 1 que NO son el logo corporatiu.
El logo es identifica per estar a la posicio x0~98, top~49.

Us:
    cd backend
    venv\Scripts\activate
    python extract_images_from_pdfs.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import pdfplumber
from app import create_app, db
from app.models import FitxaTecnica, VersioFitxa

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')


def is_certification(img, page_width):
    """Detecta si una imatge es una certificacio (posicio superior dreta, entre capsalera i camps).
    Les certificacions de Farinera Coromina estan a:
    - x0 > 300 (part dreta del document)
    - top entre 80 i 250 (entre capsalera i primer camp)
    - mida raonable (width > 30, height > 30)
    """
    x0 = img.get('x0', 0)
    top = img.get('top', 0)
    w = img.get('width', 0)
    h = img.get('height', 0)
    return x0 > 300 and 80 < top < 250 and w > 30 and h > 30


def extract_images(pdf_path, art_codi, fitxa_id):
    """Extreu imatges de certificacio de la pagina 1 d'un PDF."""
    extracted = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return extracted

            page = pdf.pages[0]
            imgs = page.images

            # Filtrar: nomes imatges que son certificacions
            cert_imgs = [img for img in imgs if is_certification(img, page.width)]

            if not cert_imgs:
                return extracted

            # Crear directori d'imatges
            img_dir = os.path.join(UPLOAD_DIR, art_codi, 'img')
            os.makedirs(img_dir, exist_ok=True)

            for i, img in enumerate(cert_imgs):
                try:
                    x0 = img['x0']
                    top = img['top']
                    w = img['width']
                    h = img['height']

                    # Extreure la regio de la imatge
                    crop = page.crop((x0, top, x0 + w, top + h))
                    pil_img = crop.to_image(resolution=200).original

                    filename = f'certificacio_{i + 1}.png'
                    filepath = os.path.join(img_dir, filename)
                    pil_img.save(filepath, 'PNG')

                    url = f'/api/fitxes/{fitxa_id}/imatges/{filename}'
                    extracted.append({'filename': filename, 'url': url})
                except Exception as e:
                    print(f'    Error extraient img {i}: {e}')

    except Exception as e:
        print(f'  Error obrint PDF: {e}')

    return extracted


def main():
    app = create_app()

    with app.app_context():
        versions = VersioFitxa.query.filter(
            VersioFitxa.fitxer_pdf != None,
            VersioFitxa.fitxer_pdf != '',
            VersioFitxa.activa == True,
        ).all()

        print(f'Versions actives amb PDF: {len(versions)}')

        total_imatges = 0
        fitxes_amb_img = 0

        for versio in versions:
            pdf_path = versio.fitxer_pdf
            if not pdf_path or not os.path.exists(pdf_path):
                continue

            fitxa = db.session.get(FitxaTecnica, versio.fitxa_id)
            if not fitxa:
                continue

            imgs = extract_images(pdf_path, fitxa.art_codi, fitxa.id)

            if imgs:
                fitxes_amb_img += 1
                total_imatges += len(imgs)

                # Guardar la primera imatge al contingut com a camp 'certificacio_img'
                contingut = versio.contingut or {}
                if len(imgs) == 1:
                    contingut['certificacio_img'] = imgs[0]['url']
                else:
                    # Multiples imatges: guardar-les totes
                    for j, img in enumerate(imgs):
                        contingut[f'certificacio_img_{j + 1}'] = img['url']

                versio.contingut = contingut
                # Force SQLAlchemy to detect JSON change
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(versio, 'contingut')
                db.session.commit()

                print(f'  {fitxa.art_codi}: {len(imgs)} imatges extretes')

        print(f'\n{"=" * 50}')
        print(f'Extraccio completada!')
        print(f'  Fitxes amb imatges: {fitxes_amb_img}')
        print(f'  Total imatges: {total_imatges}')


if __name__ == '__main__':
    main()
