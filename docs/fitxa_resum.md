# Fitxes Tècniques

**URL:** http://fitxesfc.agrienergia.local/ · **Estat:** en producció (adopció parcial) · **Període dev:** 2026 (34,4 h acumulades)

---

## Descripció

Aplicació web per crear, versionar i distribuir les **fitxes tècniques de producte** de Farinera Coromina. Cada edició genera una nova versió immutable amb autoria, motiu del canvi i timestamp. La distribució als destins (FTP de clients, carpetes de xarxa internes) és automàtica i traçada. Inclou generació de PDF i importació de Word per migrar contingut existent.
## Necessitat

Abans, les fitxes tècniques vivien en una carpeta de xarxa amb un Excel manual de versions, pujades manuals al FTP de cada client i risc constant de desincronització (el PDF al FTP no coincideix amb el de la xarxa interna, o amb el de SAP B1). Procés regulat per normativa alimentària amb necessitat de demostrar versionat i autoria si Sanitat ho demana.
## Recursos dedicats

| Concepte | Valor |
|---|---|
| Hores de desenvolupament | **34,4 h** |
| Cost intern estimat (a 33,5 €/h cost empresa) | **1.152 €** |
| Stack tècnic | Python · Flask · React + Vite · PostgreSQL · WeasyPrint (PDF) · FTP + SMB (distribució) |

## Retorn

### Quantitatiu

Adopció encara parcial; no es disposa de mesura empírica d'estalvi de temps. L'aplicació funciona però els usuaris no l'utilitzen al 100 %, per la qual cosa qualsevol xifra ara seria especulativa.

### Qualitatiu

- **Versionat immutable:** historial complet de cada fitxa amb autoria, motiu i data. Resposta immediata a qualsevol auditoria.
- **Distribució automàtica multi-destí:** copia a carpeta de xarxa SMB + pujada al FTP amb nom estàndard `{codi_article}.pdf`, amb reintents i registre d'estat (`pendent`/`ok`/`error`).
- **Compliance regulatori:** documentació trazable conforme a la normativa alimentària (RD 677/2016).
- **Generació PDF consistent:** una sola plantilla per a tots els productes; cap més format manual diferent per persona.
- **Importació Word:** facilita la migració del contingut històric sense haver de re-mecanografiar.
- **Control d'accés:** rol `qualitat` (CRUD) i rol `consulta` (només lectura), amb autenticació SSO.

## Veredicte

**Inversió de 1.152 € en una infraestructura que, quan estigui plenament adoptada, eliminarà el risc principal del procés (versions desincronitzades entre destins) i deixarà l'empresa coberta per a auditories regulatòries.** Pendent mesura d'estalvi de temps un cop l'ús sigui al 100 %.
