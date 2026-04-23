import { useState, useEffect, useCallback, useRef } from 'react';
import DOMPurify from 'dompurify';
import RichEditor from './RichEditor';
import { api } from '../api/client';

function arrayMove(arr, from, to) {
  const next = [...arr];
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}

/* ============================================================
   DEFAULT SECTIONS
   ============================================================ */
const DEFAULT_SECTIONS = [
  {
    id: 'ident', label: 'Identificación del producto / Identificació del producte',
    items: [
      { key: 'codi_referencia', label: 'Código de referencia / Codi de referència', type: 'text' },
      { key: 'certificacio', label: 'Certificación / Certificació', type: 'textarea' },
      { key: 'denominacio_comercial', label: 'Denominación comercial del Producto / Denominació comercial del producte', type: 'textarea' },
      { key: 'denominacio_juridica', label: 'Denominación jurídica del producto / Denominació jurídica del producte', type: 'textarea' },
      { key: 'codi_ean', label: 'Código EAN / Codi EAN', type: 'text' },
      { key: 'descripcio', label: 'Descripción del producto / Descripció del producte', type: 'textarea' },
      { key: 'origen', label: 'Origen del Producto y Procedencia del cereal / Origen del producte i procedència del cereal', type: 'textarea' },
      { key: 'ingredients', label: 'Ingredientes / Ingredients', type: 'textarea' },
      { key: 'alergens', label: 'Alérgenos / Al·lèrgens', type: 'textarea' },
      { key: 'ogm', label: 'OGM', type: 'textarea' },
      { key: 'irradiacio', label: 'Irradiación – Ionización / Irradiació – Ionització', type: 'textarea' },
    ],
  },
  {
    id: 'caract', label: 'Características / Característiques',
    items: [
      { key: 'caract_organoleptiques', label: 'Características organolépticas / Característiques organolèptiques', type: 'textarea' },
      { key: 'fisicoquimiques', label: 'Características físico-químicas / Característiques fisicoquímiques', type: 'table' },
      { key: 'reologiques', label: 'Características reológicas / Característiques reològiques', type: 'table' },
      { key: 'microbiologiques', label: 'Características Microbiológicas / Característiques microbiològiques', type: 'table' },
    ],
  },
  {
    id: 'contam', label: 'Parámetros de Contaminantes / Paràmetres de contaminants',
    items: [
      { key: 'micotoxines', label: 'Micotoxinas / Micotoxines', type: 'table' },
      { key: 'alcaloides', label: 'Alcaloides del cornezuelo / Alcaloides del sègol banyut', type: 'table' },
      { key: 'metalls_pesants', label: 'Metales pesados / Metalls pesants', type: 'table' },
      { key: 'contaminants_altres', label: 'Otros contaminantes / Altres contaminants', type: 'table' },
      { key: 'pesticidas', label: 'Pesticidas / Pesticides', type: 'textarea' },
    ],
  },
  {
    id: 'nutri', label: 'Valores nutricionales / Valors nutricionals',
    items: [
      { key: 'valors_nutricionals', label: 'Valores nutricionales / Valors nutricionals', type: 'table' },
    ],
  },
  {
    id: 'comerc', label: 'Información comercial / Informació comercial',
    items: [
      { key: 'presentacio_envase', label: 'Presentación – envase / Presentació – envàs', type: 'textarea' },
      { key: 'us_previst', label: 'Uso previsto / Ús previst', type: 'textarea' },
      { key: 'condicions_emmagatzematge', label: "Condiciones de almacenaje / Condicions d'emmagatzematge", type: 'textarea' },
      { key: 'condicions_transport', label: 'Condiciones de transporte / Condicions de transport', type: 'textarea' },
      { key: 'vida_util', label: 'Vida útil del producto / Vida útil del producte', type: 'textarea' },
      { key: 'legislacio_aplicable', label: 'Otra legislación aplicable / Altra legislació aplicable', type: 'textarea' },
      { key: 'fabricat_per', label: 'Producto fabricado para / Producte fabricat per a', type: 'textarea' },
      { key: 'vigencia_document', label: 'Vigencia del documento / Vigència del document', type: 'textarea' },
    ],
  },
];

/* ============================================================
   SECTION NAV SIDEBAR
   ============================================================ */
function SectionNav({ sections, contingut, activeSection }) {
  const countFilled = (items) => {
    return items.filter((it) => {
      const v = contingut[it.key];
      if (it.type === 'table') return Array.isArray(v) && v.length > 0 && v.some((r) => r.parametre || r.valor);
      return v && String(v).trim().length > 0;
    }).length;
  };

  const scrollTo = (sectionId) => {
    const el = document.getElementById(`section-${sectionId}`);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <nav className="section-nav" aria-label="Seccions del formulari">
      {sections.map((s) => {
        const filled = countFilled(s.items);
        const total = s.items.length;
        const pct = total > 0 ? Math.round((filled / total) * 100) : 0;
        const isActive = activeSection === s.id;

        return (
          <button
            key={s.id}
            type="button"
            className={`section-nav-item ${isActive ? 'active' : ''}`}
            onClick={() => scrollTo(s.id)}
          >
            <div className="section-nav-label">{s.label}</div>
            <div className="section-nav-progress">
              <div className="section-nav-bar">
                <div className="section-nav-bar-fill" style={{ width: `${pct}%` }} />
              </div>
              <span className="section-nav-count">{filled}/{total}</span>
            </div>
          </button>
        );
      })}
    </nav>
  );
}

/* ============================================================
   ITEM TOOLBAR (ordenar + moure + eliminar)
   ============================================================ */
function ItemToolbar({ onMoveUp, onMoveDown, onMoveToSection, onRemove, canUp, canDown, sections, currentSection }) {
  const [showMove, setShowMove] = useState(false);
  const otherSections = sections?.filter((s) => s.id !== currentSection) || [];

  return (
    <div className="item-toolbar">
      <button type="button" disabled={!canUp} onClick={onMoveUp} title="Pujar">&#9650;</button>
      <button type="button" disabled={!canDown} onClick={onMoveDown} title="Baixar">&#9660;</button>
      {otherSections.length > 0 && (
        <div style={{ position: 'relative' }}>
          <button type="button" onClick={() => setShowMove(!showMove)} title="Moure a altra secció">&#8644;</button>
          {showMove && (
            <div className="move-menu">
              {otherSections.map((s) => (
                <button key={s.id} type="button" onClick={() => { onMoveToSection(s.id); setShowMove(false); }}>
                  {s.label}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
      {onRemove && <button type="button" onClick={onRemove} title="Eliminar" className="remove">&times;</button>}
    </div>
  );
}

/* ============================================================
   EDITABLE FIELD
   ============================================================ */
function EditableField({ label, value, onChange, onRemove, multiline, readOnly, toolbar }) {
  if (readOnly) {
    if (!value || !String(value).trim()) return null;
    const hasHtml = typeof value === 'string' && value.includes('<');
    return (
      <div className="pdf-field">
        <div className="pdf-field-label">{label}</div>
        {hasHtml ? (
          <div className="pdf-field-value" dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(value) }} />
        ) : (
          <div className="pdf-field-value">{value}</div>
        )}
      </div>
    );
  }
  return (
    <div className="pdf-field">
      <div className="pdf-field-label">
        {label}
        {toolbar}
      </div>
      {multiline ? (
        <RichEditor value={value || ''} onChange={onChange} />
      ) : (
        <input className="pdf-field-input" type="text" value={value || ''} onChange={(e) => onChange(e.target.value)} />
      )}
    </div>
  );
}

/* ============================================================
   EDITABLE TABLE
   ============================================================ */
// Subtítols que van dins la taula (com al PDF real)
const TABLE_SUBTITLES = {
  microbiologiques: 'Parámetros microbiológicos / Paràmetres microbiològics',
  valors_nutricionals: 'Valores nutricionales (por 100g) / Valors nutricionals (per 100g)',
};

function EditableTable({ label, rows, onChange, onRemove, readOnly, toolbar, tableKey }) {
  if (readOnly) {
    if (!rows || rows.length === 0) return null;
    const subtitle = tableKey && TABLE_SUBTITLES[tableKey];
    return (
      <div className="pdf-field">
        <div className="pdf-section-title">{label}</div>
        <table className="pdf-param-table">
          {subtitle && (
            <thead>
              <tr><td colSpan={2} className="pdf-table-subtitle">{subtitle}</td></tr>
              <tr><th>Parámetro / Paràmetre</th><th>Valor</th></tr>
            </thead>
          )}
          {!subtitle && (
            <thead><tr><th>Parámetro / Paràmetre</th><th>Valor</th></tr></thead>
          )}
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                <td className={row.sub ? 'sub-param' : ''} style={{ padding: '5px 10px' }}>{row.parametre}</td>
                <td style={{ padding: '5px 10px' }}>{row.valor}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  const addRow = () => onChange([...rows, { parametre: '', valor: '' }]);
  const removeRow = (i) => onChange(rows.filter((_, idx) => idx !== i));
  const updateRow = (i, field, value) => {
    const updated = [...rows];
    updated[i] = { ...updated[i], [field]: value };
    onChange(updated);
  };

  return (
    <div className="pdf-field">
      <div className="pdf-section-title">
        {label}
        {toolbar}
      </div>
      <table className="pdf-param-table">
        <thead><tr><th>Parámetro / Paràmetre</th><th>Valor</th><th style={{ width: '36px' }}></th></tr></thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              <td><input value={row.parametre || ''} onChange={(e) => updateRow(i, 'parametre', e.target.value)} placeholder="Parametre" /></td>
              <td><input value={row.valor || ''} onChange={(e) => updateRow(i, 'valor', e.target.value)} placeholder="Valor" /></td>
              <td><button type="button" className="pdf-row-remove" onClick={() => removeRow(i)}>&times;</button></td>
            </tr>
          ))}
        </tbody>
      </table>
      <button type="button" className="pdf-add-row" onClick={addRow}>+ Afegir fila</button>
    </div>
  );
}

/* ============================================================
   EDITABLE IMAGE
   ============================================================ */
function EditableImage({ label, value, onChange, readOnly, toolbar, fitxaId }) {
  const [uploading, setUploading] = useState(false);

  if (readOnly) {
    if (!value) return null;
    return (
      <div className="pdf-field">
        <div className="pdf-field-label">{label}</div>
        <div className="pdf-image-container">
          <img src={value} alt={label} className="pdf-image" />
        </div>
      </div>
    );
  }

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file || !fitxaId) return;
    setUploading(true);
    try {
      const result = await api.pujarImatge(fitxaId, file);
      onChange(result.url);
    } catch (err) {
      alert(`Error pujant imatge: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="pdf-field">
      <div className="pdf-field-label">
        {label}
        {toolbar}
      </div>
      {value ? (
        <div className="pdf-image-container">
          <img src={value} alt={label} className="pdf-image" />
          <button type="button" className="outline secondary btn-sm" style={{ marginTop: '0.5rem' }}
            onClick={() => onChange('')}>Treure imatge</button>
        </div>
      ) : (
        <label className="pdf-image-upload" aria-busy={uploading}>
          {uploading ? 'Pujant...' : 'Fes clic per pujar una imatge'}
          <input type="file" accept="image/*" onChange={handleUpload} disabled={uploading}
            style={{ display: 'none' }} />
        </label>
      )}
    </div>
  );
}

/* ============================================================
   ADD ITEM INLINE
   ============================================================ */
function AddItemInline({ onAdd }) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState(null);
  const [label, setLabel] = useState('');

  const confirm = () => {
    if (!label.trim()) return;
    const key = label.trim().toLowerCase().replace(/[^a-z0-9\u00e0\u00e8\u00e9\u00ed\u00f2\u00f3\u00fa\u00ef\u00fc\u00e7 ]/g, '').replace(/\s+/g, '_');
    onAdd(key, label.trim(), mode);
    setLabel(''); setMode(null); setOpen(false);
  };

  if (!open) return (
    <button type="button" className="pdf-add-element-btn" onClick={() => setOpen(true)}>+ Afegir camp, taula o imatge</button>
  );
  if (!mode) return (
    <div className="pdf-add-element-panel">
      <button type="button" className="outline btn-sm" onClick={() => setMode('textarea')}>Camp de text</button>
      <button type="button" className="outline btn-sm" onClick={() => setMode('table')}>Taula</button>
      <button type="button" className="outline btn-sm" onClick={() => setMode('image')}>Imatge</button>
      <button type="button" className="outline secondary btn-sm" onClick={() => { setOpen(false); setMode(null); }}>Cancel\u00b7lar</button>
    </div>
  );
  return (
    <div className="pdf-add-element-panel">
      <input type="text" value={label} onChange={(e) => setLabel(e.target.value)}
        placeholder="Nom (ex: Vitamines, Niquel...)" autoFocus
        onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); confirm(); } }}
        style={{ flex: 1, margin: 0 }} />
      <button type="button" className="btn-sm" onClick={confirm}>Afegir</button>
      <button type="button" className="outline secondary btn-sm" onClick={() => { setMode(null); setLabel(''); }}>Cancel\u00b7lar</button>
    </div>
  );
}

/* ============================================================
   PDF PAGE HEADER (replicat del PDF real)
   ============================================================ */
function formatDate(isoStr) {
  if (!isoStr) return '-';
  try {
    const d = new Date(isoStr);
    if (isNaN(d)) return isoStr;
    return d.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' });
  } catch { return isoStr; }
}

function PdfPageHeader({ rev, dataRevisio, dataComprovacio }) {
  return (
    <table className="pdf-header">
      <tbody>
        <tr>
          <td className="pdf-header-logo" rowSpan={3}>
            <img src="/logo.png" alt="Farinera Coromina" className="pdf-logo-img" />
          </td>
          <td className="pdf-header-title" rowSpan={3}>FICHA T&Eacute;CNICA / FITXA T&Egrave;CNICA</td>
          <td className="pdf-header-meta">Rev.: {rev ?? '-'}</td>
        </tr>
        <tr><td className="pdf-header-meta">Fecha/Data Rev: {dataRevisio || '-'}</td></tr>
        <tr><td className="pdf-header-meta">Fecha/Data Comprov.: {dataComprovacio || '-'}</td></tr>
      </tbody>
    </table>
  );
}

function PdfPageFooter({ page, totalPages }) {
  return (
    <div className="pdf-footer-wrapper">
      <div className="pdf-footer">
        AGRI-ENERGIA, S.A.<br />
        C/ Girona, 155 &ndash; 17820 Banyoles &ndash; GIRONA &ndash; Tel. 972 58 33 63<br />
        www.farineracoromina.com
      </div>
      {page != null && (
        <div className="pdf-page-number">{page}</div>
      )}
    </div>
  );
}

/* ============================================================
   NOTES REGULATÒRIES per taula (com al PDF real)
   ============================================================ */
const TABLE_NOTES = {
  microbiologiques: 'Establecidos como criterio interno en base RD 1286/1984 actualmente derogado. / Establerts com a criteri intern en base RD 1286/1984 actualment derogat.',
  micotoxines: 'Según Reglamento 2023/915 relativo a los límites máximos de determinados contaminantes en los alimentos y posteriores modificaciones que pueda haber. / Segons Reglament 2023/915 relatiu als límits màxims de determinats contaminants en els aliments i posteriors modificacions que hi pugui haver.',
  alcaloides: 'Según Reglamento 2023/915 relativo a los límites máximos de determinados contaminantes en los alimentos y posteriores modificaciones que pueda haber. / Segons Reglament 2023/915 relatiu als límits màxims de determinats contaminants en els aliments i posteriors modificacions que hi pugui haver.',
  metalls_pesants: 'Según Reglamento 2023/915 relativo a los límites máximos de determinados contaminantes en los alimentos y posteriores modificaciones que pueda haber. / Segons Reglament 2023/915 relatiu als límits màxims de determinats contaminants en els aliments i posteriors modificacions que hi pugui haver.',
  valors_nutricionals: 'Los valores pueden variar al tratarse de producto natural. / Els valors poden variar en tractar-se de producte natural.',
  fisicoquimiques: 'Según RD 677/2016 / Segons RD 677/2016.',
  reologiques: 'Según RD 677/2016 / Segons RD 677/2016.',
};

/* ============================================================
   PDF DOCUMENT VIEW (mode lectura - exportat per DetallFitxa)
   ============================================================ */
export function PdfDocumentView({ contingut, versio }) {
  if (!contingut || Object.keys(contingut).length === 0) {
    return <div className="empty-state">Sense contingut registrat per aquesta versió.</div>;
  }

  // Prioritzar dades del model VersioFitxa, fallback a contingut
  const rev = versio?.num_versio ?? contingut.rev ?? '-';
  const dataRevisio = versio?.created_at ? formatDate(versio.created_at) : (contingut.data_revisio || '-');
  const dataComprovacio = versio?.data_comprovacio ? formatDate(versio.data_comprovacio) : (contingut.data_comprovacio || '-');

  const knownKeys = new Set();
  DEFAULT_SECTIONS.forEach((s) => s.items.forEach((it) => knownKeys.add(it.key)));
  const extraKeys = Object.keys(contingut).filter(
    (k) => !knownKeys.has(k) && !['rev', 'data_revisio', 'data_comprovacio', '_cert_config'].includes(k) && !k.startsWith('certificacio_img')
  );

  // Recollir imatges de certificacio del contingut
  const certImgs = Object.entries(contingut)
    .filter(([k, v]) => k.startsWith('certificacio_img') && v && typeof v === 'string')
    .map(([k, v]) => ({ key: k, url: v }));

  // Agrupar seccions que tenen dades
  const sectionsWithData = DEFAULT_SECTIONS.filter((section) =>
    section.items.some((it) => {
      if (it.key.startsWith('certificacio_img')) return false; // mostrades apart
      const v = contingut[it.key];
      return v !== undefined && v !== '' && (Array.isArray(v) ? v.length > 0 : true);
    })
  );

  const hasExtras = extraKeys.length > 0;
  const totalPages = sectionsWithData.length + (hasExtras ? 1 : 0);

  return (
    <div className="pdf-document pdf-view-mode">
      {sectionsWithData.map((section, si) => (
        <div key={section.id} className="pdf-page">
          <PdfPageHeader rev={rev} dataRevisio={dataRevisio} dataComprovacio={dataComprovacio} />

          {/* Imatges certificacio a la primera pagina */}
          {si === 0 && certImgs.length > 0 && (() => {
            const cfg = contingut._cert_config || { align: 'right', size: 60 };
            const justify = cfg.align === 'left' ? 'flex-start' : cfg.align === 'center' ? 'center' : 'flex-end';
            return (
              <div className="pdf-cert-images" style={{ justifyContent: justify }}>
                {certImgs.map((img) => (
                  <img key={img.key} src={img.url} alt="Certificació" className="pdf-cert-img"
                    style={{ height: `${cfg.size}px` }} />
                ))}
              </div>
            );
          })()}

          {section.items.map((it) => {
            const v = contingut[it.key];
            const hasData = v !== undefined && v !== '' && (Array.isArray(v) ? v.length > 0 : true);
            if (!hasData) return null;

            return (
              <div key={it.key}>
                {it.type === 'table'
                  ? <EditableTable label={it.label} rows={Array.isArray(v) ? v : []} readOnly tableKey={it.key} />
                  : it.type === 'image'
                  ? <EditableImage label={it.label} value={v} readOnly />
                  : <EditableField label={it.label} value={v} readOnly />
                }
                {TABLE_NOTES[it.key] && (
                  <div className="pdf-table-note">{TABLE_NOTES[it.key]}</div>
                )}
              </div>
            );
          })}

          <PdfPageFooter page={si + 1} />
          {si < totalPages - 1 && <div className="pdf-page-divider" />}
        </div>
      ))}

      {extraKeys.length > 0 && (
        <div className="pdf-page">
          <PdfPageHeader rev={rev} dataRevisio={dataRevisio} dataComprovacio={dataComprovacio} />
          <div className="pdf-section-title">Camps addicionals</div>
          {extraKeys.map((key) => {
            const v = contingut[key];
            if (Array.isArray(v)) return <EditableTable key={key} label={key} rows={v} readOnly />;
            if (typeof v === 'string' && v.startsWith('/api/fitxes/') && v.includes('/imatges/')) {
              return <EditableImage key={key} label={key} value={v} readOnly />;
            }
            if (v && String(v).trim()) return <EditableField key={key} label={key} value={v} readOnly />;
            return null;
          })}
          <PdfPageFooter page={totalPages} />
        </div>
      )}
    </div>
  );
}

/* ============================================================
   CERT IMAGE EDITOR (imatges de certificacio editables amb posicio i mida)
   ============================================================ */
function CertImageEditor({ contingut, onChange, fitxaId }) {
  const [uploading, setUploading] = useState(false);
  const imgs = Object.entries(contingut)
    .filter(([k, v]) => k.startsWith('certificacio_img') && v && typeof v === 'string')
    .map(([k, v]) => ({ key: k, url: v }));

  // Configuracio guardada al contingut: { align, size }
  const config = contingut._cert_config || { align: 'right', size: 60 };
  const setConfig = (newConf) => onChange('_cert_config', { ...config, ...newConf });

  const handleReplace = async (key, e) => {
    const file = e.target.files[0];
    if (!file || !fitxaId) return;
    setUploading(true);
    try {
      const result = await api.pujarImatge(fitxaId, file);
      onChange(key, result.url);
    } catch (err) {
      alert(`Error pujant imatge: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleAdd = async (e) => {
    const file = e.target.files[0];
    if (!file || !fitxaId) return;
    setUploading(true);
    try {
      const result = await api.pujarImatge(fitxaId, file);
      const existing = Object.keys(contingut).filter((k) => k.startsWith('certificacio_img'));
      const nextIdx = existing.length + 1;
      const key = existing.length === 0 ? 'certificacio_img' : `certificacio_img_${nextIdx}`;
      onChange(key, result.url);
    } catch (err) {
      alert(`Error pujant imatge: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleRemove = (key) => {
    onChange(key, '');
  };

  if (imgs.length === 0) {
    return (
      <div className="pdf-cert-editor">
        <label className="pdf-cert-add-empty" aria-busy={uploading}>
          {uploading ? 'Pujant...' : '+ Afegir imatge de certificació'}
          <input type="file" accept="image/*" onChange={handleAdd}
            style={{ display: 'none' }} disabled={uploading} />
        </label>
      </div>
    );
  }

  return (
    <div className="pdf-cert-editor">
      {/* Controls de posicio i mida */}
      <div className="pdf-cert-controls">
        <div className="pdf-cert-control-group">
          <span className="pdf-cert-control-label">Posició:</span>
          {['left', 'center', 'right'].map((a) => (
            <button key={a} type="button"
              className={`pdf-cert-align-btn ${config.align === a ? 'active' : ''}`}
              onClick={() => setConfig({ align: a })}>
              {a === 'left' ? 'Esquerra' : a === 'center' ? 'Centre' : 'Dreta'}
            </button>
          ))}
        </div>
        <div className="pdf-cert-control-group">
          <span className="pdf-cert-control-label">Mida: {config.size}px</span>
          <input type="range" min="30" max="150" value={config.size}
            onChange={(e) => setConfig({ size: parseInt(e.target.value) })}
            style={{ width: '120px', margin: 0 }} />
        </div>
      </div>

      {/* Imatges amb la posicio i mida configurades */}
      <div className="pdf-cert-images" style={{ justifyContent: config.align === 'left' ? 'flex-start' : config.align === 'center' ? 'center' : 'flex-end' }}>
        {imgs.map((img) => (
          <div key={img.key} className="pdf-cert-item">
            <img src={img.url} alt="Certificació" className="pdf-cert-img"
              style={{ height: `${config.size}px` }} />
            <div className="pdf-cert-actions">
              <label className="pdf-cert-action-btn" title="Substituir" aria-busy={uploading}>
                &#8635;
                <input type="file" accept="image/*" onChange={(e) => handleReplace(img.key, e)}
                  style={{ display: 'none' }} disabled={uploading} />
              </label>
              <button type="button" className="pdf-cert-action-btn remove" title="Treure"
                onClick={() => handleRemove(img.key)}>&times;</button>
            </div>
          </div>
        ))}
        <label className="pdf-cert-add" title="Afegir imatge" aria-busy={uploading}
          style={{ height: `${config.size}px` }}>
          {uploading ? '...' : '+'}
          <input type="file" accept="image/*" onChange={handleAdd}
            style={{ display: 'none' }} disabled={uploading} />
        </label>
      </div>
    </div>
  );
}

/* ============================================================
   FITXA FORM (editor amb sidebar nav)
   ============================================================ */
function FitxaForm({ initialData, onSubmit, isNew, versio, fitxaId }) {
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [activeSection, setActiveSection] = useState(null);
  const formRef = useRef(null);
  const c = initialData.contingut || {};

  const [form, setForm] = useState({
    art_codi: initialData.art_codi || '',
    nom_producte: initialData.nom_producte || '',
    categoria: initialData.categoria || '',
    descripcio_canvi: initialData.descripcio_canvi || '',
  });

  const [contingut, setContingut] = useState(c);

  const updateForm = (newForm) => { setForm(newForm); setDirty(true); };
  const updateContingut = useCallback((fn) => { setContingut(fn); setDirty(true); }, []);

  useEffect(() => {
    const handler = (e) => {
      if (dirty) { e.preventDefault(); e.returnValue = ''; }
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [dirty]);

  const [sections, setSections] = useState(() => {
    const knownKeys = new Set();
    DEFAULT_SECTIONS.forEach((s) => s.items.forEach((it) => knownKeys.add(it.key)));

    const base = DEFAULT_SECTIONS.map((s) => ({
      ...s,
      items: s.items.map((it) => ({ ...it, id: `item_${s.id}_${it.key}` })),
    }));

    const extraItems = [];
    Object.entries(c).forEach(([key, val]) => {
      if (!knownKeys.has(key) && !['rev', 'data_revisio', 'data_comprovacio'].includes(key)) {
        extraItems.push({ key, label: key, type: Array.isArray(val) ? 'table' : 'textarea', id: `item_extra_${key}` });
      }
    });
    if (extraItems.length > 0) {
      base.push({ id: 'extra', label: 'Camps addicionals', items: extraItems });
    }
    return base;
  });

  // Track which section is visible via IntersectionObserver
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id.replace('section-', ''));
          }
        }
      },
      { rootMargin: '-100px 0px -60% 0px', threshold: 0 }
    );
    sections.forEach((s) => {
      const el = document.getElementById(`section-${s.id}`);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, [sections]);

  const update = (key, value) => { setContingut((prev) => ({ ...prev, [key]: value })); setDirty(true); };

  const removeItem = (sectionId, itemKey) => {
    setSections((prev) => prev.map((s) =>
      s.id === sectionId ? { ...s, items: s.items.filter((it) => it.key !== itemKey) } : s
    ));
    setContingut((prev) => { const next = { ...prev }; delete next[itemKey]; return next; });
  };

  const addItemToSection = (sectionId, key, label, type) => {
    if (key in contingut) { alert(`El camp "${key}" ja existeix.`); return; }
    setSections((prev) => prev.map((s) =>
      s.id === sectionId ? { ...s, items: [...s.items, { key, label, type, id: `item_${sectionId}_${key}_${Date.now()}` }] } : s
    ));
    setContingut((prev) => ({
      ...prev,
      [key]: type === 'table' ? [{ parametre: '', valor: '' }] : '',
    }));
  };

  const removeSection = (sectionId) => {
    if (!confirm('Eliminar la secció i tots els seus camps?')) return;
    const section = sections.find((s) => s.id === sectionId);
    if (!section) return;
    setContingut((prev) => {
      const next = { ...prev };
      section.items.forEach((it) => delete next[it.key]);
      return next;
    });
    setSections((prev) => prev.filter((s) => s.id !== sectionId));
  };

  const addSection = () => {
    const label = prompt('Nom de la nova secció:');
    if (!label || !label.trim()) return;
    const id = `custom_${Date.now()}`;
    setSections((prev) => [...prev, { id, label: label.trim(), items: [] }]);
  };

  const moveItemInSection = (sectionId, itemIdx, direction) => {
    setSections((prev) => prev.map((s) => {
      if (s.id !== sectionId) return s;
      const newIdx = itemIdx + direction;
      if (newIdx < 0 || newIdx >= s.items.length) return s;
      return { ...s, items: arrayMove(s.items, itemIdx, newIdx) };
    }));
    setDirty(true);
  };

  const moveItemToSection = (fromSectionId, itemKey, toSectionId) => {
    setSections((prev) => {
      const next = prev.map((s) => ({ ...s, items: [...s.items] }));
      const fromSection = next.find((s) => s.id === fromSectionId);
      const toSection = next.find((s) => s.id === toSectionId);
      if (!fromSection || !toSection) return prev;
      const itemIdx = fromSection.items.findIndex((it) => it.key === itemKey);
      if (itemIdx === -1) return prev;
      const [item] = fromSection.items.splice(itemIdx, 1);
      toSection.items.push(item);
      return next;
    });
    setDirty(true);
  };

  const moveSectionUp = (idx) => {
    if (idx <= 0) return;
    setSections((prev) => arrayMove(prev, idx, idx - 1));
  };
  const moveSectionDown = (idx) => {
    if (idx >= sections.length - 1) return;
    setSections((prev) => arrayMove(prev, idx, idx + 1));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.descripcio_canvi.trim()) { alert('Cal indicar la descripció del canvi.'); return; }
    setSaving(true);
    try {
      await onSubmit({
        ...form,
        contingut: {
          ...contingut,
          codi_referencia: form.art_codi || contingut.codi_referencia,
          denominacio_comercial: contingut.denominacio_comercial || form.nom_producte,
        },
      });
      setDirty(false);
    } finally { setSaving(false); }
  };

  return (
    <form onSubmit={handleSubmit} ref={formRef}>
      {/* Barra superior */}
      <div className="pdf-topbar">
        <div className="pdf-topbar-fields">
          <label>
            Codi article
            <input value={form.art_codi} onChange={(e) => updateForm({ ...form, art_codi: e.target.value })}
              required disabled={!isNew} placeholder="Ex: 60360" />
          </label>
          <label style={{ flex: 2 }}>
            Nom producte
            <input value={form.nom_producte} onChange={(e) => updateForm({ ...form, nom_producte: e.target.value })}
              required placeholder="Ex: HARINA PANADERIA W150" />
          </label>
          <label>
            Categoria
            <input value={form.categoria} onChange={(e) => updateForm({ ...form, categoria: e.target.value })} placeholder="Ex: Farines" />
          </label>
        </div>
        <div className="pdf-topbar-row2">
          <label style={{ flex: 1, margin: 0 }}>
            Descripció del canvi *
            <textarea value={form.descripcio_canvi} onChange={(e) => updateForm({ ...form, descripcio_canvi: e.target.value })}
              required placeholder="Ex: S'actualitzen els valors de W i P/L. S'afegeix el niquel als contaminants."
              rows={2} style={{ resize: 'vertical', minHeight: '46px' }} />
          </label>
          <button type="submit" aria-busy={saving} disabled={saving} className="pdf-save-btn">
            {saving ? 'Desant...' : isNew ? 'Crear fitxa' : 'Desar (nova versió)'}
          </button>
        </div>
      </div>

      {/* Layout amb sidebar */}
      <div className="form-with-sidebar">
        <SectionNav sections={sections} contingut={contingut} activeSection={activeSection} />

        {/* Document */}
        <div className="pdf-document">
          {/* Capsalera — logo + dades de versio (read-only) */}
          <PdfPageHeader
            rev={isNew ? '-' : (versio?.num_versio ?? contingut.rev ?? '-')}
            dataRevisio={versio?.created_at ? formatDate(versio.created_at) : (contingut.data_revisio || '-')}
            dataComprovacio={versio?.data_comprovacio ? formatDate(versio.data_comprovacio) : (contingut.data_comprovacio || '-')}
          />

          {/* Imatges de certificacio (editables) */}
          <CertImageEditor contingut={contingut} onChange={update} fitxaId={fitxaId} />

          {/* Seccions */}
          {sections.map((section, si) => (
            <div key={section.id} id={`section-${section.id}`} className="pdf-section-block">
              {/* Accions secció (només visibles al hover) */}
              <div className="pdf-section-actions-bar">
                <button type="button" disabled={si === 0} onClick={() => moveSectionUp(si)} title="Pujar secció">&#9650;</button>
                <button type="button" disabled={si === sections.length - 1} onClick={() => moveSectionDown(si)} title="Baixar secció">&#9660;</button>
                <button type="button" onClick={() => removeSection(section.id)} title="Eliminar secció" className="remove">&times;</button>
              </div>

              {section.items.map((it, ii) => {
                const tb = (
                  <ItemToolbar
                    canUp={ii > 0}
                    canDown={ii < section.items.length - 1}
                    onMoveUp={() => moveItemInSection(section.id, ii, -1)}
                    onMoveDown={() => moveItemInSection(section.id, ii, 1)}
                    onMoveToSection={(toId) => moveItemToSection(section.id, it.key, toId)}
                    onRemove={() => removeItem(section.id, it.key)}
                    sections={sections}
                    currentSection={section.id}
                  />
                );

                if (it.type === 'table') return (
                  <EditableTable key={it.id} label={it.label}
                    rows={Array.isArray(contingut[it.key]) ? contingut[it.key] : []}
                    onChange={(v) => update(it.key, v)}
                    toolbar={tb} />
                );
                if (it.type === 'image') return (
                  <EditableImage key={it.id} label={it.label}
                    value={contingut[it.key]}
                    onChange={(v) => update(it.key, v)}
                    fitxaId={fitxaId}
                    toolbar={tb} />
                );
                return (
                  <EditableField key={it.id} label={it.label}
                    value={contingut[it.key]}
                    onChange={(v) => update(it.key, v)}
                    multiline={it.type === 'textarea'}
                    toolbar={tb} />
                );
              })}

              <AddItemInline onAdd={(key, label, type) => addItemToSection(section.id, key, label, type)} />
            </div>
          ))}

          {/* Afegir secció */}
          <div style={{ marginTop: '1.5rem' }}>
            <button type="button" className="pdf-add-section-btn" onClick={addSection}>+ Afegir secció</button>
          </div>

          {/* Peu */}
          <div className="pdf-footer">
            AGRI-ENERGIA, S.A. &mdash; C/ Girona, 155 &ndash; 17820 Banyoles &ndash; GIRONA &mdash; www.farineracoromina.com
          </div>
        </div>
      </div>
    </form>
  );
}

export default FitxaForm;
