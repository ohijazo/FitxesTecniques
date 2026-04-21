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
    titol: 'Què és aquesta aplicació?',
    contingut: (
      <>
        <p>
          <strong>Fitxes Tècniques</strong> és el sistema centralitzat per crear, gestionar i distribuir
          les fitxes tècniques de productes del departament de qualitat de Farinera Coromina.
        </p>
        <p>Substitueix el procés manual anterior (carpeta de xarxa + FileZilla + Excel de versions) per un sistema únic amb:</p>
        <ul>
          <li>Control de versions integrat</li>
          <li>Distribució automàtica al FTP</li>
          <li>Historial complet de canvis</li>
          <li>Generació de PDF</li>
        </ul>
      </>
    ),
  },
  {
    id: 'fitxes',
    titol: 'Gestió de fitxes tècniques',
    contingut: (
      <>
        <h4>Pàgina principal — Llista de fitxes</h4>
        <p>
          La pàgina principal mostra totes les fitxes amb el codi, nom, revisió, estat i estat de distribució.
          Pots cercar per codi o nom i filtrar per estat.
        </p>
        <HelpImg src="/help/llista.png" alt="Llista de fitxes tècniques amb filtres i accions ràpides" />

        <h4>Crear una fitxa nova</h4>
        <ol>
          <li>Prem <strong>+ Nova fitxa</strong> al menú o a la pàgina principal</li>
          <li>Tria entre <strong>Pujar Word</strong> (extreu les dades automàticament del .docx) o <strong>Crear manualment</strong></li>
        </ol>
        <HelpImg src="/help/nova.png" alt="Pantalla de creació: triar entre pujar Word o crear manualment" />
        <ol start={3}>
          <li>Omple els camps del formulari per seccions</li>
          <li>Indica una descripció del canvi (obligatòria)</li>
          <li>Prem <strong>Crear fitxa</strong></li>
          <li>Un diàleg et preguntarà si vols distribuir-la immediatament</li>
        </ol>

        <h4>Editar una fitxa</h4>
        <ol>
          <li>Obre la fitxa des de la llista principal</li>
          <li>Prem <strong>Editar / Nova versió</strong></li>
          <li>Modifica els camps necessaris</li>
          <li>Indica que has canviat a "Descripció del canvi"</li>
          <li>Prem <strong>Desar (nova versió)</strong> — es crea una nova revisió automàticament</li>
        </ol>
        <HelpImg src="/help/editor.png" alt="Editor de fitxa amb navegació lateral per seccions i barra de progrés" />
        <div className="help-tip">
          <strong>Navegació per seccions:</strong> A l'esquerra del formulari hi ha un menú amb totes les seccions
          i una barra de progrés que indica quants camps estan omplerts.
        </div>

        <h4>Visualitzar una fitxa</h4>
        <p>
          La vista de detall mostra la fitxa amb un format similar al PDF real, incloent la capçalera
          amb el logo, número de revisió i dates.
        </p>
        <HelpImg src="/help/detall.png" alt="Detall de fitxa amb capçalera, contingut i accions" />
        <p>Pots canviar entre tres pestanyes:</p>
        <ul>
          <li><strong>Contingut</strong> — visualització de la fitxa</li>
          <li><strong>Versions</strong> — historial de totes les revisions amb comparació de canvis</li>
          <li><strong>Distribucions</strong> — historial de distribucions i opció de distribuir</li>
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
          Cada vegada que edites una fitxa es crea una <strong>nova versió</strong> (revisió).
          Les versions anteriors es conserven i mai es sobreescriuen.
        </p>
        <HelpImg src="/help/versions.png" alt="Timeline de versions amb comparació de canvis" />

        <h4>Comparar versions</h4>
        <p>
          A la pestanya <strong>Versions</strong> del detall de la fitxa, prem <strong>Veure canvis</strong>
          al costat de qualsevol versió per veure exactament què ha canviat respecte la versió anterior.
          Els camps afegits es mostren en verd i els eliminats en vermell.
        </p>

        <h4>Restaurar una versió</h4>
        <p>
          Pots tornar a activar una versió anterior prement <strong>Restaurar</strong>.
          Això no elimina cap versió, simplement canvia quina és l'activa.
        </p>

        <h4>Veure PDF de qualsevol versió</h4>
        <p>
          Prem <strong>Veure PDF</strong> al costat de qualsevol versió per generar i visualitzar
          el PDF corresponent a aquella revisió.
        </p>
      </>
    ),
  },
  {
    id: 'distribucio',
    titol: 'Distribució',
    contingut: (
      <>
        <p>
          La distribució envia el PDF de la fitxa tècnica als destins configurats (FTP, carpeta de xarxa, etc.).
        </p>

        <h4>Com distribuir</h4>
        <ol>
          <li>Obre la fitxa que vols distribuir</li>
          <li>Prem el botó <strong>Distribuir</strong></li>
          <li>Selecciona els destins on vols enviar-la</li>
          <li>Prem <strong>Distribuir als destins seleccionats</strong></li>
          <li>Veuràs el resultat per cada destí (ok o error)</li>
          <li>Si la distribució és correcta, es mostra la URL pública del fitxer</li>
        </ol>
        <HelpImg src="/help/distribucio.png" alt="Panell de distribució amb selecció de destins i resultats" />

        <h4>Indicadors a la llista</h4>
        <p>A la llista principal, cada fitxa mostra l'estat de distribució:</p>
        <ul>
          <li><span className="dist-badge dist-ok" style={{ display: 'inline-flex' }}><span className="dist-icon">&#10003;</span> Distribuït</span> — tots els destins ok</li>
          <li><span className="dist-badge dist-partial" style={{ display: 'inline-flex' }}><span className="dist-icon">&#9681;</span> Parcial</span> — alguns destins ok, altres pendents</li>
          <li><span className="dist-badge dist-pending" style={{ display: 'inline-flex' }}><span className="dist-icon">&#9675;</span> Pendent</span> — cap destí distribuït</li>
          <li><span className="dist-badge dist-error" style={{ display: 'inline-flex' }}><span className="dist-icon">&times;</span> Error</span> — algun destí ha fallat</li>
        </ul>

        <h4>Historial</h4>
        <p>
          A la pestanya <strong>Distribucions</strong> del detall pots veure l'historial complet
          amb data, usuari, estat i URL per cada distribució.
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
          La pàgina <strong>Control de revisions</strong> (al menú principal) mostra una vista global
          de totes les fitxes amb les seves dades tècniques clau, equivalent a l'Excel PR09.02.
        </p>
        <HelpImg src="/help/control.png" alt="Control de revisions amb estadístiques i filtres" />

        <h4>Estadístiques</h4>
        <p>
          A la part superior hi ha targetes amb comptadors (total, publicades, esborranys, obsoletes, caducades).
          Fes clic a qualsevol targeta per filtrar ràpidament.
        </p>

        <h4>Filtre "Requereix atenció"</h4>
        <p>
          Activa aquest filtre per veure només les fitxes que necessiten acció: caducades (&gt;2 anys sense revisar)
          o en estat esborrany. Les files es mostren amb color per facilitar la identificació.
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
          L'aplicació genera automàticament el PDF de la fitxa tècnica a partir de les dades introduïdes.
          El PDF segueix la plantilla corporativa amb capçalera, logo i peu de pàgina.
        </p>

        <h4>Descarregar</h4>
        <ul>
          <li><strong>Des del detall:</strong> botó "Descarregar PDF"</li>
          <li><strong>Des de la llista:</strong> botó "PDF" a les accions ràpides</li>
          <li><strong>Versió concreta:</strong> botó "Veure PDF" a la timeline de versions</li>
        </ul>

        <h4>Vista prèvia</h4>
        <p>
          Prem <strong>Vista prèvia PDF</strong> al detall per veure el PDF directament al navegador
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
        <p>Només els administradors poden eliminar fitxes. El procés requereix:</p>
        <ol>
          <li>Prem el botó vermell <strong>Eliminar</strong> al detall de la fitxa</li>
          <li>Indica el <strong>motiu</strong> de l'eliminació (obligatori)</li>
          <li>Marca si vols <strong>esborrar també del FTP</strong></li>
          <li>Confirma amb la teva <strong>contrasenya</strong></li>
        </ol>
        <HelpImg src="/help/eliminar.png" alt="Modal d'eliminació amb motiu, opció FTP i confirmació amb contrasenya" />
        <div className="help-tip">
          <strong>Registre d'audit:</strong> Totes les eliminacions queden registrades a
          <strong> Admin &gt; Eliminacions</strong> amb el codi, producte, motiu, qui i quan.
        </div>
      </>
    ),
  },
  {
    id: 'admin',
    titol: 'Administració',
    contingut: (
      <>
        <p>
          Les opcions d'administració es troben al menú <strong>Configuració</strong> de la barra superior
          (només visible per administradors). Inclou:
        </p>

        <h4>Control revisions</h4>
        <p>
          Vista global de totes les fitxes amb dades tècniques clau. També accessible des del menú Configuració.
        </p>

        <h4>Destins</h4>
        <p>
          Configura on es distribueixen les fitxes (FTP, carpeta de xarxa, SAP).
          Per a FTP cal indicar host, usuari, contrasenya i si usa TLS.
        </p>

        <h4>Usuaris</h4>
        <p>Gestiona els usuaris de l'aplicació. Hi ha tres rols:</p>
        <ul>
          <li><strong>Admin</strong> — accés complet (crear, editar, eliminar, configurar)</li>
          <li><strong>Editor</strong> — crear i editar fitxes, distribuir</li>
          <li><strong>Visualitzador</strong> — només lectura</li>
        </ul>

        <h4>Camps (Seccions)</h4>
        <p>
          Defineix l'estructura de les fitxes: quines seccions i camps apareixen al formulari.
          Pots afegir, editar, reordenar i eliminar camps.
        </p>

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
          <li>Pots <strong>cercar</strong> fitxes per codi o nom a la pàgina principal</li>
          <li>Els <strong>filtres d'estat</strong> es recorden entre sessions</li>
          <li>Si tanques el navegador amb <strong>canvis sense desar</strong>, rebràs un avís</li>
          <li>Les <strong>taules de paràmetres</strong> (fisicoquímiques, microbiològiques...) permeten afegir i eliminar files dinàmicament</li>
          <li>Pots <strong>moure camps entre seccions</strong> amb el botó &#8644; que apareix al passar el ratolí</li>
          <li>Pots <strong>reordenar seccions</strong> amb les fletxes &#9650;&#9660;</li>
          <li>La <strong>verificació automàtica</strong> compara les dades de l'app amb el PDF original del FTP</li>
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
