import { useState, useEffect, useCallback, useRef } from 'react';
import DOMPurify from 'dompurify';
import RichEditor from './RichEditor';

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
    id: 'ident', label: 'Identificacio del producte',
    items: [
      { key: 'codi_referencia', label: 'Codigo de referencia / Codi de referencia', type: 'text' },
      { key: 'denominacio_comercial', label: 'Denominacion comercial del Producto', type: 'textarea' },
      { key: 'denominacio_juridica', label: 'Denominacion juridica del producto', type: 'textarea' },
      { key: 'codi_ean', label: 'Codigo EAN', type: 'text' },
      { key: 'descripcio', label: 'Descripcion del producto', type: 'textarea' },
      { key: 'origen', label: 'Origen del Producto y Procedencia del cereal', type: 'textarea' },
      { key: 'ingredients', label: 'Ingredientes / Ingredients', type: 'textarea' },
      { key: 'alergens', label: 'Alergenos / Al\u00b7lergens', type: 'textarea' },
      { key: 'ogm', label: 'OGM', type: 'textarea' },
      { key: 'irradiacio', label: 'Irradiacion \u2013 Ionizacion', type: 'textarea' },
    ],
  },
  {
    id: 'caract', label: 'Caracteristiques',
    items: [
      { key: 'caract_organoleptiques', label: 'Caracteristicas organolepticas', type: 'textarea' },
      { key: 'fisicoquimiques', label: 'Caracteristicas fisico \u2013 quimicas', type: 'table' },
      { key: 'reologiques', label: 'Caracteristicas reologicas', type: 'table' },
      { key: 'microbiologiques', label: 'Caracteristicas Microbiologicas', type: 'table' },
    ],
  },
  {
    id: 'contam', label: 'Parametros de Contaminantes',
    items: [
      { key: 'micotoxines', label: 'Micotoxinas / Micotoxines', type: 'table' },
      { key: 'alcaloides', label: 'Alcaloides del cornezuelo', type: 'table' },
      { key: 'metalls_pesants', label: 'Metales pesados / Metalls pesants', type: 'table' },
      { key: 'contaminants_altres', label: 'Altres contaminants', type: 'table' },
      { key: 'pesticidas', label: 'Pesticidas / Pesticides', type: 'textarea' },
    ],
  },
  {
    id: 'nutri', label: 'Valors nutricionals',
    items: [
      { key: 'valors_nutricionals', label: 'Valores nutricionales', type: 'table' },
    ],
  },
  {
    id: 'comerc', label: 'Informacio comercial',
    items: [
      { key: 'presentacio_envase', label: 'Presentacion \u2013 envase', type: 'textarea' },
      { key: 'us_previst', label: 'Uso previsto / Us previst', type: 'textarea' },
      { key: 'condicions_emmagatzematge', label: "Condiciones de almacenaje", type: 'textarea' },
      { key: 'condicions_transport', label: 'Condiciones de transporte', type: 'textarea' },
      { key: 'vida_util', label: 'Vida util del producto', type: 'textarea' },
      { key: 'legislacio_aplicable', label: 'Otra legislacion aplicable', type: 'textarea' },
      { key: 'fabricat_per', label: 'Producto fabricado para', type: 'textarea' },
      { key: 'vigencia_document', label: 'Vigencia del documento', type: 'textarea' },
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
          <button type="button" onClick={() => setShowMove(!showMove)} title="Moure a altra seccio">&#8644;</button>
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
function EditableTable({ label, rows, onChange, onRemove, readOnly, toolbar }) {
  if (readOnly) {
    if (!rows || rows.length === 0) return null;
    return (
      <div className="pdf-field">
        <div className="pdf-section-title">{label}</div>
        <table className="pdf-param-table">
          <thead><tr><th>Parametro</th><th>Valor</th></tr></thead>
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
        <thead><tr><th>Parametro</th><th>Valor</th><th style={{ width: '36px' }}></th></tr></thead>
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
   ADD ITEM INLINE
   ============================================================ */
function AddItemInline({ onAdd }) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState(null);
  const [label, setLabel] = useState('');

  const confirm = () => {
    if (!label.trim()) return;
    const key = label.trim().toLowerCase().replace(/[^a-z0-9\u00e0\u00e8\u00e9\u00ed\u00f2\u00f3\u00fa\u00ef\u00fc\u00e7 ]/g, '').replace(/\s+/g, '_');
    onAdd(key, label.trim(), mode === 'table' ? 'table' : 'textarea');
    setLabel(''); setMode(null); setOpen(false);
  };

  if (!open) return (
    <button type="button" className="pdf-add-element-btn" onClick={() => setOpen(true)}>+ Afegir camp o taula</button>
  );
  if (!mode) return (
    <div className="pdf-add-element-panel">
      <button type="button" className="outline btn-sm" onClick={() => setMode('textarea')}>Camp de text</button>
      <button type="button" className="outline btn-sm" onClick={() => setMode('table')}>Taula</button>
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
          <td className="pdf-header-title" rowSpan={3}>FICHA T&Eacute;CNICA</td>
          <td className="pdf-header-meta">Rev.: {rev ?? '-'}</td>
        </tr>
        <tr><td className="pdf-header-meta">Fecha Revisi&oacute;n: {dataRevisio || '-'}</td></tr>
        <tr><td className="pdf-header-meta">Fecha Comprovaci&oacute;n: {dataComprovacio || '-'}</td></tr>
      </tbody>
    </table>
  );
}

function PdfPageFooter() {
  return (
    <div className="pdf-footer">
      AGRI-ENERGIA, S.A.<br />
      C/ Girona, 155 &ndash; 17820 Banyoles &ndash; GIRONA &ndash; Tel. 972 58 33 63<br />
      www.farineracoromina.com
    </div>
  );
}

/* ============================================================
   PDF DOCUMENT VIEW (mode lectura - exportat per DetallFitxa)
   ============================================================ */
export function PdfDocumentView({ contingut, versio }) {
  if (!contingut || Object.keys(contingut).length === 0) {
    return <div className="empty-state">Sense contingut registrat per aquesta versio.</div>;
  }

  // Prioritzar dades del model VersioFitxa, fallback a contingut
  const rev = versio?.num_versio ?? contingut.rev ?? '-';
  const dataRevisio = versio?.created_at ? formatDate(versio.created_at) : (contingut.data_revisio || '-');
  const dataComprovacio = versio?.data_comprovacio ? formatDate(versio.data_comprovacio) : (contingut.data_comprovacio || '-');

  const knownKeys = new Set();
  DEFAULT_SECTIONS.forEach((s) => s.items.forEach((it) => knownKeys.add(it.key)));
  const extraKeys = Object.keys(contingut).filter(
    (k) => !knownKeys.has(k) && !['rev', 'data_revisio', 'data_comprovacio'].includes(k)
  );

  // Agrupar seccions que tenen dades
  const sectionsWithData = DEFAULT_SECTIONS.filter((section) =>
    section.items.some((it) => {
      const v = contingut[it.key];
      return v !== undefined && v !== '' && (Array.isArray(v) ? v.length > 0 : true);
    })
  );

  return (
    <div className="pdf-document pdf-view-mode">
      {sectionsWithData.map((section, si) => (
        <div key={section.id} className="pdf-page">
          <PdfPageHeader rev={rev} dataRevisio={dataRevisio} dataComprovacio={dataComprovacio} />

          {section.items.map((it) => it.type === 'table'
            ? <EditableTable key={it.key} label={it.label} rows={Array.isArray(contingut[it.key]) ? contingut[it.key] : []} readOnly />
            : <EditableField key={it.key} label={it.label} value={contingut[it.key]} readOnly />
          )}

          <PdfPageFooter />
          {si < sectionsWithData.length - 1 && <div className="pdf-page-divider" />}
        </div>
      ))}

      {extraKeys.length > 0 && (
        <div className="pdf-page">
          <PdfPageHeader rev={rev} dataRevisio={dataRevisio} dataComprovacio={dataComprovacio} />
          <div className="pdf-section-title">Camps addicionals</div>
          {extraKeys.map((key) => {
            const v = contingut[key];
            if (Array.isArray(v)) return <EditableTable key={key} label={key} rows={v} readOnly />;
            if (v && String(v).trim()) return <EditableField key={key} label={key} value={v} readOnly />;
            return null;
          })}
          <PdfPageFooter />
        </div>
      )}
    </div>
  );
}

/* ============================================================
   FITXA FORM (editor amb sidebar nav)
   ============================================================ */
function FitxaForm({ initialData, onSubmit, isNew, versio }) {
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
    if (!confirm('Eliminar la seccio i tots els seus camps?')) return;
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
    const label = prompt('Nom de la nova seccio:');
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
    if (!form.descripcio_canvi.trim()) { alert('Cal indicar la descripcio del canvi.'); return; }
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
            Descripcio del canvi *
            <textarea value={form.descripcio_canvi} onChange={(e) => updateForm({ ...form, descripcio_canvi: e.target.value })}
              required placeholder="Ex: S'actualitzen els valors de W i P/L. S'afegeix el niquel als contaminants."
              rows={2} style={{ resize: 'vertical', minHeight: '46px' }} />
          </label>
          <button type="submit" aria-busy={saving} disabled={saving} className="pdf-save-btn">
            {saving ? 'Desant...' : isNew ? 'Crear fitxa' : 'Desar (nova versio)'}
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

          {/* Seccions */}
          {sections.map((section, si) => (
            <div key={section.id} id={`section-${section.id}`} className="pdf-section-block">
              <div className="pdf-section-header">
                <div className="pdf-section-header-label">{section.label}</div>
                <div className="pdf-section-header-actions">
                  <button type="button" disabled={si === 0} onClick={() => moveSectionUp(si)} title="Pujar seccio">&#9650;</button>
                  <button type="button" disabled={si === sections.length - 1} onClick={() => moveSectionDown(si)} title="Baixar seccio">&#9660;</button>
                  <button type="button" onClick={() => removeSection(section.id)} title="Eliminar seccio" className="remove">&times;</button>
                </div>
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

                return it.type === 'table' ? (
                  <EditableTable key={it.id} label={it.label}
                    rows={Array.isArray(contingut[it.key]) ? contingut[it.key] : []}
                    onChange={(v) => update(it.key, v)}
                    toolbar={tb} />
                ) : (
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

          {/* Afegir seccio */}
          <div style={{ marginTop: '1.5rem' }}>
            <button type="button" className="pdf-add-section-btn" onClick={addSection}>+ Afegir seccio</button>
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
