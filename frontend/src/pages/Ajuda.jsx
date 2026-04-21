import { useState } from 'react';

function HelpImg({ src, alt }) {
  const [error, setError] = useState(false);
  if (error) return null;
  return (
    <div className="help-img-wrapper">
      <img src={src} alt={alt} className="help-img" onError={() => setError(true)} loading="lazy" />
      <div className="help-img-caption">{alt}</div>
    </div>
  );
}

const SECTIONS = [
  {
    id: 'intro',
    titol: 'Que es aquesta aplicacio?',
    contingut: (
      <>
        <p>
          <strong>Fitxes Tecniques</strong> es el sistema centralitzat per crear, gestionar i distribuir
          les fitxes tecniques de productes del departament de qualitat de Farinera Coromina.
        </p>
        <p>Substitueix el proces manual anterior (carpeta de xarxa + FileZilla + Excel de versions) per un sistema unic amb:</p>
        <ul>
          <li>Control de versions integrat</li>
          <li>Distribucio automatica al FTP</li>
          <li>Historial complet de canvis</li>
          <li>Generacio de PDF</li>
        </ul>
      </>
    ),
  },
  {
    id: 'fitxes',
    titol: 'Gestio de fitxes tecniques',
    contingut: (
      <>
        <h4>Pagina principal — Llista de fitxes</h4>
        <p>
          La pagina principal mostra totes les fitxes amb el codi, nom, revisio, estat i estat de distribucio.
          Pots cercar per codi o nom i filtrar per estat.
        </p>
        <HelpImg src="/help/llista.png" alt="Llista de fitxes tecniques amb filtres i accions rapides" />

        <h4>Crear una fitxa nova</h4>
        <ol>
          <li>Prem <strong>+ Nova fitxa</strong> al menu o a la pagina principal</li>
          <li>Tria entre <strong>Pujar Word</strong> (extreu les dades automaticament del .docx) o <strong>Crear manualment</strong></li>
        </ol>
        <HelpImg src="/help/nova.png" alt="Pantalla de creacio: triar entre pujar Word o crear manualment" />
        <ol start={3}>
          <li>Omple els camps del formulari per seccions</li>
          <li>Indica una descripcio del canvi (obligatoria)</li>
          <li>Prem <strong>Crear fitxa</strong></li>
          <li>Un dialeg et preguntara si vols distribuir-la immediatament</li>
        </ol>

        <h4>Editar una fitxa</h4>
        <ol>
          <li>Obre la fitxa des de la llista principal</li>
          <li>Prem <strong>Editar / Nova versio</strong></li>
          <li>Modifica els camps necessaris</li>
          <li>Indica que has canviat a "Descripcio del canvi"</li>
          <li>Prem <strong>Desar (nova versio)</strong> — es crea una nova revisio automaticament</li>
        </ol>
        <HelpImg src="/help/editor.png" alt="Editor de fitxa amb navegacio lateral per seccions i barra de progres" />
        <div className="help-tip">
          <strong>Navegacio per seccions:</strong> A l'esquerra del formulari hi ha un menu amb totes les seccions
          i una barra de progres que indica quants camps estan omplerts.
        </div>

        <h4>Visualitzar una fitxa</h4>
        <p>
          La vista de detall mostra la fitxa amb un format similar al PDF real, incloent la capsalera
          amb el logo, numero de revisio i dates.
        </p>
        <HelpImg src="/help/detall.png" alt="Detall de fitxa amb capsalera, contingut i accions" />
        <p>Pots canviar entre tres pestanyes:</p>
        <ul>
          <li><strong>Contingut</strong> — visualitzacio de la fitxa</li>
          <li><strong>Versions</strong> — historial de totes les revisions amb comparacio de canvis</li>
          <li><strong>Distribucions</strong> — historial de distribucions i opcio de distribuir</li>
        </ul>
      </>
    ),
  },
  {
    id: 'versions',
    titol: 'Control de versions',
    contingut: (
      <>
        <p>
          Cada vegada que edites una fitxa es crea una <strong>nova versio</strong> (revisio).
          Les versions anteriors es conserven i mai es sobreescriuen.
        </p>
        <HelpImg src="/help/versions.png" alt="Timeline de versions amb comparacio de canvis" />

        <h4>Comparar versions</h4>
        <p>
          A la pestanya <strong>Versions</strong> del detall de la fitxa, prem <strong>Veure canvis</strong>
          al costat de qualsevol versio per veure exactament que ha canviat respecte la versio anterior.
          Els camps afegits es mostren en verd i els eliminats en vermell.
        </p>

        <h4>Restaurar una versio</h4>
        <p>
          Pots tornar a activar una versio anterior prement <strong>Restaurar</strong>.
          Aixo no elimina cap versio, simplement canvia quina es l'activa.
        </p>

        <h4>Veure PDF de qualsevol versio</h4>
        <p>
          Prem <strong>Veure PDF</strong> al costat de qualsevol versio per generar i visualitzar
          el PDF corresponent a aquella revisio.
        </p>
      </>
    ),
  },
  {
    id: 'distribucio',
    titol: 'Distribucio',
    contingut: (
      <>
        <p>
          La distribucio envia el PDF de la fitxa tecnica als destins configurats (FTP, carpeta de xarxa, etc.).
        </p>

        <h4>Com distribuir</h4>
        <ol>
          <li>Obre la fitxa que vols distribuir</li>
          <li>Prem el boto <strong>Distribuir</strong></li>
          <li>Selecciona els destins on vols enviar-la</li>
          <li>Prem <strong>Distribuir als destins seleccionats</strong></li>
          <li>Veuras el resultat per cada desti (ok o error)</li>
          <li>Si la distribucio es correcta, es mostra la URL publica del fitxer</li>
        </ol>
        <HelpImg src="/help/distribucio.png" alt="Panell de distribucio amb seleccio de destins i resultats" />

        <h4>Indicadors a la llista</h4>
        <p>A la llista principal, cada fitxa mostra l'estat de distribucio:</p>
        <ul>
          <li><span className="dist-badge dist-ok" style={{ display: 'inline-flex' }}><span className="dist-icon">&#10003;</span> Distribuit</span> — tots els destins ok</li>
          <li><span className="dist-badge dist-partial" style={{ display: 'inline-flex' }}><span className="dist-icon">&#9681;</span> Parcial</span> — alguns destins ok, altres pendents</li>
          <li><span className="dist-badge dist-pending" style={{ display: 'inline-flex' }}><span className="dist-icon">&#9675;</span> Pendent</span> — cap desti distribuit</li>
          <li><span className="dist-badge dist-error" style={{ display: 'inline-flex' }}><span className="dist-icon">&times;</span> Error</span> — algun desti ha fallat</li>
        </ul>

        <h4>Historial</h4>
        <p>
          A la pestanya <strong>Distribucions</strong> del detall pots veure l'historial complet
          amb data, usuari, estat i URL per cada distribucio.
        </p>
      </>
    ),
  },
  {
    id: 'control',
    titol: 'Control de revisions',
    contingut: (
      <>
        <p>
          La pagina <strong>Control de revisions</strong> (al menu principal) mostra una vista global
          de totes les fitxes amb les seves dades tecniques clau, equivalent a l'Excel PR09.02.
        </p>
        <HelpImg src="/help/control.png" alt="Control de revisions amb estadistiques i filtres" />

        <h4>Estadistiques</h4>
        <p>
          A la part superior hi ha targetes amb comptadors (total, publicades, esborranys, obsoletes, caducades).
          Fes clic a qualsevol targeta per filtrar rapidament.
        </p>

        <h4>Filtre "Requereix atencio"</h4>
        <p>
          Activa aquest filtre per veure nomes les fitxes que necessiten accio: caducades (&gt;2 anys sense revisar)
          o en estat esborrany. Les files es mostren amb color per facilitar la identificacio.
        </p>

        <h4>Exportar a Excel</h4>
        <p>
          Prem <strong>Exportar a Excel</strong> per descarregar totes les dades en format .xlsx.
        </p>
      </>
    ),
  },
  {
    id: 'pdf',
    titol: 'PDF',
    contingut: (
      <>
        <h4>Generar PDF</h4>
        <p>
          L'aplicacio genera automaticament el PDF de la fitxa tecnica a partir de les dades introduides.
          El PDF segueix la plantilla corporativa amb capsalera, logo i peu de pagina.
        </p>

        <h4>Descarregar</h4>
        <ul>
          <li><strong>Des del detall:</strong> boto "Descarregar PDF"</li>
          <li><strong>Des de la llista:</strong> boto "PDF" a les accions rapides</li>
          <li><strong>Versio concreta:</strong> boto "Veure PDF" a la timeline de versions</li>
        </ul>

        <h4>Vista previa</h4>
        <p>
          Prem <strong>Vista previa PDF</strong> al detall per veure el PDF directament al navegador
          sense descarregar-lo.
        </p>
      </>
    ),
  },
  {
    id: 'eliminar',
    titol: 'Eliminar fitxes',
    contingut: (
      <>
        <p>Nomes els administradors poden eliminar fitxes. El proces requereix:</p>
        <ol>
          <li>Prem el boto vermell <strong>Eliminar</strong> al detall de la fitxa</li>
          <li>Indica el <strong>motiu</strong> de l'eliminacio (obligatori)</li>
          <li>Marca si vols <strong>esborrar tambe del FTP</strong></li>
          <li>Confirma amb la teva <strong>contrasenya</strong></li>
        </ol>
        <HelpImg src="/help/eliminar.png" alt="Modal d'eliminacio amb motiu, opcio FTP i confirmacio amb contrasenya" />
        <div className="help-tip">
          <strong>Registre d'audit:</strong> Totes les eliminacions queden registrades a
          <strong> Admin &gt; Eliminacions</strong> amb el codi, producte, motiu, qui i quan.
        </div>
      </>
    ),
  },
  {
    id: 'admin',
    titol: 'Administracio',
    contingut: (
      <>
        <p>Les seccions d'administracio son accessibles nomes per usuaris amb rol <strong>admin</strong>.</p>

        <h4>Camps (Seccions)</h4>
        <p>
          Defineix l'estructura de les fitxes: quines seccions i camps apareixen al formulari.
          Pots afegir, editar, reordenar i eliminar camps.
        </p>

        <h4>Destins</h4>
        <p>
          Configura on es distribueixen les fitxes (FTP, carpeta de xarxa, SAP).
          Per a FTP cal indicar host, usuari, contrasenya i si usa TLS.
        </p>

        <h4>Usuaris</h4>
        <p>Gestiona els usuaris de l'aplicacio. Hi ha tres rols:</p>
        <ul>
          <li><strong>Admin</strong> — acces complet (crear, editar, eliminar, configurar)</li>
          <li><strong>Editor</strong> — crear i editar fitxes, distribuir</li>
          <li><strong>Visualitzador</strong> — nomes lectura</li>
        </ul>

        <h4>Eliminacions</h4>
        <p>Historial de totes les fitxes que s'han eliminat, amb motiu i responsable.</p>
      </>
    ),
  },
  {
    id: 'dreceres',
    titol: 'Consells i dreceres',
    contingut: (
      <>
        <ul>
          <li>Pots <strong>cercar</strong> fitxes per codi o nom a la pagina principal</li>
          <li>Els <strong>filtres d'estat</strong> es recorden entre sessions</li>
          <li>Si tanques el navegador amb <strong>canvis sense desar</strong>, rebras un avis</li>
          <li>Les <strong>taules de parametres</strong> (fisicoquimiques, microbiologiques...) permeten afegir i eliminar files dinamicament</li>
          <li>Pots <strong>moure camps entre seccions</strong> amb el boto &#8644; que apareix al passar el ratoli</li>
          <li>Pots <strong>reordenar seccions</strong> amb les fletxes &#9650;&#9660;</li>
          <li>La <strong>verificacio automatica</strong> compara les dades de l'app amb el PDF original del FTP</li>
        </ul>
      </>
    ),
  },
];

function Ajuda() {
  const [activeSection, setActiveSection] = useState('intro');

  return (
    <div className="help-layout">
      <nav className="help-nav">
        <h3 style={{ fontSize: '0.95rem', margin: '0 0 0.75rem', color: 'var(--gray-900)' }}>Ajuda</h3>
        {SECTIONS.map((s) => (
          <button
            key={s.id}
            type="button"
            className={`help-nav-item ${activeSection === s.id ? 'active' : ''}`}
            onClick={() => {
              setActiveSection(s.id);
              const el = document.getElementById(`help-${s.id}`);
              if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }}
          >
            {s.titol}
          </button>
        ))}
      </nav>

      <div className="help-content">
        {SECTIONS.map((s) => (
          <div key={s.id} id={`help-${s.id}`} className="help-section card">
            <h2 style={{ fontSize: '1.2rem', marginBottom: '1rem', color: 'var(--brand)' }}>{s.titol}</h2>
            {s.contingut}
          </div>
        ))}
      </div>
    </div>
  );
}

export default Ajuda;
