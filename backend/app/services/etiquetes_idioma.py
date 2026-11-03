"""Títols de la fitxa tècnica per idioma.

Els títols de la plantilla estan escrits en format bilingüe
"Castellano / Català". Per a 'es' i 'ca' n'hi ha prou amb quedar-se amb la
part corresponent; per a 'en' i 'pt' cal el diccionari d'aquí sota.

Les traduccions a l'anglès i al portuguès s'han de fer validar per Qualitat.
"""

IDIOMES = ('ca', 'es', 'en', 'pt', 'it')

NOMS_IDIOMA = {
    'ca': 'Català',
    'es': 'Castellà',
    'en': 'Anglès',
    'pt': 'Portuguès',
    'it': 'Italià',
}

# Títols que no segueixen el patró "castellà / català" o que tenen un text
# propi per a cada idioma. Clau = text tal com apareix a la plantilla.
ETIQUETES = {
    'FICHA TÉCNICA / FITXA TÈCNICA': {
        'es': 'FICHA TÉCNICA', 'ca': 'FITXA TÈCNICA',
        'en': 'TECHNICAL DATA SHEET', 'pt': 'FICHA TÉCNICA'},
    'Fecha/Data Rev': {
        'es': 'Fecha Rev.', 'ca': 'Data Rev.',
        'en': 'Rev. date', 'pt': 'Data rev.'},
    'Fecha/Data Comprov.': {
        'es': 'Fecha Comprov.', 'ca': 'Data Comprov.',
        'en': 'Check date', 'pt': 'Data verif.'},
    'Valor': {'en': 'Value', 'pt': 'Valor'},
    'OGM': {'en': 'GMO', 'pt': 'OGM'},
    'Código de referencia / Codi de referència': {
        'en': 'Reference code', 'pt': 'Código de referência'},
    'Certificación / Certificació': {
        'en': 'Certification', 'pt': 'Certificação'},
    'Denominación comercial del Producto / Denominació comercial del producte': {
        'en': 'Product trade name', 'pt': 'Denominação comercial do produto'},
    'Denominación jurídica del producto / Denominació jurídica del producte': {
        'en': 'Legal name of the product', 'pt': 'Denominação legal do produto'},
    'Código EAN / Codi EAN': {
        'en': 'EAN code', 'pt': 'Código EAN'},
    'Descripción del producto / Descripció del producte': {
        'en': 'Product description', 'pt': 'Descrição do produto'},
    'Origen del Producto y Procedencia del cereal / Origen del producte i procedència del cereal': {
        'en': 'Product origin and cereal provenance',
        'pt': 'Origem do produto e proveniência do cereal'},
    'Ingredientes / Ingredients': {
        'en': 'Ingredients', 'pt': 'Ingredientes'},
    'Alérgenos / Al·lèrgens': {
        'en': 'Allergens', 'pt': 'Alergénios'},
    'Irradiación – Ionización / Irradiació – Ionització': {
        'en': 'Irradiation – Ionisation', 'pt': 'Irradiação – Ionização'},
    'Características organolépticas / Característiques organolèptiques': {
        'en': 'Organoleptic characteristics', 'pt': 'Características organoléticas'},
    'Características físico-químicas / Característiques fisicoquímiques': {
        'en': 'Physicochemical characteristics', 'pt': 'Características físico-químicas'},
    'Características reológicas / Característiques reològiques': {
        'en': 'Rheological characteristics', 'pt': 'Características reológicas'},
    'Características Microbiológicas / Característiques microbiològiques': {
        'en': 'Microbiological characteristics', 'pt': 'Características microbiológicas'},
    'Parámetros microbiológicos / Paràmetres microbiològics': {
        'en': 'Microbiological parameters', 'pt': 'Parâmetros microbiológicos'},
    'Parámetro / Paràmetre': {
        'en': 'Parameter', 'pt': 'Parâmetro'},
    'Parámetros de Contaminantes / Paràmetres de contaminants': {
        'en': 'Contaminant parameters', 'pt': 'Parâmetros de contaminantes'},
    'Micotoxinas / Micotoxines': {
        'en': 'Mycotoxins', 'pt': 'Micotoxinas'},
    'Alcaloides del cornezuelo / Alcaloides del sègol banyut': {
        'en': 'Ergot alkaloids', 'pt': 'Alcaloides da cravagem'},
    'Metales pesados / Metalls pesants': {
        'en': 'Heavy metals', 'pt': 'Metais pesados'},
    'Pesticidas / Pesticides': {
        'en': 'Pesticides', 'pt': 'Pesticidas'},
    'Valores nutricionales / Valors nutricionals': {
        'en': 'Nutritional values', 'pt': 'Valores nutricionais'},
    'Valores nutricionales (por 100g) / Valors nutricionals (per 100g)': {
        'en': 'Nutritional values (per 100 g)', 'pt': 'Valores nutricionais (por 100 g)'},
    'Presentación – envase / Presentació – envàs': {
        'en': 'Presentation – packaging', 'pt': 'Apresentação – embalagem'},
    'Uso previsto / Ús previst': {
        'en': 'Intended use', 'pt': 'Utilização prevista'},
    "Condiciones de almacenaje / Condicions d'emmagatzematge": {
        'en': 'Storage conditions', 'pt': 'Condições de armazenamento'},
    'Condiciones de transporte / Condicions de transport': {
        'en': 'Transport conditions', 'pt': 'Condições de transporte'},
    'Vida útil del producto / Vida útil del producte': {
        'en': 'Product shelf life', 'pt': 'Vida útil do produto'},
    'Otra legislación aplicable / Altra legislació aplicable': {
        'en': 'Other applicable legislation', 'pt': 'Outra legislação aplicável'},
    'Producto fabricado para / Producte fabricat per a': {
        'en': 'Product manufactured for', 'pt': 'Produto fabricado para'},
    'Vigencia del documento / Vigència del document': {
        'en': 'Document validity', 'pt': 'Validade do documento'},
    # Títols de secció i camps que només surten a la vista web (FitxaForm.jsx)
    'Identificación del producto / Identificació del producte': {
        'en': 'Product identification', 'pt': 'Identificação do produto'},
    'Características / Característiques': {
        'en': 'Characteristics', 'pt': 'Características'},
    'Otros contaminantes / Altres contaminants': {
        'en': 'Other contaminants', 'pt': 'Outros contaminantes'},
    'Información comercial / Informació comercial': {
        'en': 'Commercial information', 'pt': 'Informação comercial'},
}


# Italià (afegit després). Qualitat l'ha de revisar com l'anglès i el portuguès.
_ITALIA = {
    'FICHA TÉCNICA / FITXA TÈCNICA': 'SCHEDA TECNICA',
    'Fecha/Data Rev': 'Data rev.',
    'Fecha/Data Comprov.': 'Data verifica',
    'Valor': 'Valore',
    'OGM': 'OGM',
    'Código de referencia / Codi de referència': 'Codice di riferimento',
    'Certificación / Certificació': 'Certificazione',
    'Denominación comercial del Producto / Denominació comercial del producte': 'Denominazione commerciale del prodotto',
    'Denominación jurídica del producto / Denominació jurídica del producte': 'Denominazione legale del prodotto',
    'Código EAN / Codi EAN': 'Codice EAN',
    'Descripción del producto / Descripció del producte': 'Descrizione del prodotto',
    'Origen del Producto y Procedencia del cereal / Origen del producte i procedència del cereal': 'Origine del prodotto e provenienza del cereale',
    'Ingredientes / Ingredients': 'Ingredienti',
    'Alérgenos / Al·lèrgens': 'Allergeni',
    'Irradiación – Ionización / Irradiació – Ionització': 'Irradiazione – Ionizzazione',
    'Características organolépticas / Característiques organolèptiques': 'Caratteristiche organolettiche',
    'Características físico-químicas / Característiques fisicoquímiques': 'Caratteristiche chimico-fisiche',
    'Características reológicas / Característiques reològiques': 'Caratteristiche reologiche',
    'Características Microbiológicas / Característiques microbiològiques': 'Caratteristiche microbiologiche',
    'Parámetros microbiológicos / Paràmetres microbiològics': 'Parametri microbiologici',
    'Parámetro / Paràmetre': 'Parametro',
    'Parámetros de Contaminantes / Paràmetres de contaminants': 'Parametri dei contaminanti',
    'Micotoxinas / Micotoxines': 'Micotossine',
    'Alcaloides del cornezuelo / Alcaloides del sègol banyut': 'Alcaloidi della segale cornuta',
    'Metales pesados / Metalls pesants': 'Metalli pesanti',
    'Pesticidas / Pesticides': 'Pesticidi',
    'Valores nutricionales / Valors nutricionals': 'Valori nutrizionali',
    'Valores nutricionales (por 100g) / Valors nutricionals (per 100g)': 'Valori nutrizionali (per 100 g)',
    'Presentación – envase / Presentació – envàs': 'Presentazione – confezione',
    'Uso previsto / Ús previst': 'Uso previsto',
    "Condiciones de almacenaje / Condicions d'emmagatzematge": 'Condizioni di conservazione',
    'Condiciones de transporte / Condicions de transport': 'Condizioni di trasporto',
    'Vida útil del producto / Vida útil del producte': 'Durata di conservazione del prodotto',
    'Otra legislación aplicable / Altra legislació aplicable': 'Altra legislazione applicabile',
    'Producto fabricado para / Producte fabricat per a': 'Prodotto fabbricato per',
    'Vigencia del documento / Vigència del document': 'Validità del documento',
    'Identificación del producto / Identificació del producte': 'Identificazione del prodotto',
    'Características / Característiques': 'Caratteristiche',
    'Otros contaminantes / Altres contaminants': 'Altri contaminanti',
    'Información comercial / Informació comercial': 'Informazioni commerciali',
}
for _text, _it in _ITALIA.items():
    ETIQUETES.setdefault(_text, {})['it'] = _it


def titol_idioma(text, idioma):
    """Retorna un títol de la plantilla en l'idioma demanat.

    NOMÉS per a títols: els valors també poden contenir ' / '
    (p.ex. 'No detectado / 25g') i no s'han de tallar mai.
    'bilingue' (o buit) retorna el text tal qual.
    """
    if not text or not idioma or idioma == 'bilingue':
        return text
    propi = ETIQUETES.get(text, {}).get(idioma)
    if propi:
        return propi
    if idioma in ('es', 'ca') and ' / ' in text:
        parts = text.split(' / ', 1)
        return parts[0 if idioma == 'es' else 1].strip()
    return text
