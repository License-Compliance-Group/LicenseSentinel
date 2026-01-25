# LicenseHierarchy - Documentazione Architettura

Toolchain per la costruzione e analisi dell'albero delle dipendenze di un progetto python a partire dai suoi requirements. Include l'analisi delle licenze software, la verifica della compatibilità tra licenze e l'ispezione automatica del codice sorgente. Quest'ultima consiste nel verificare che la licenza su PyPI corrisponda a quella del repository originale

NOTA: i requiremets nel repository non sono i requiremetns del progetto, ma ipotetiche dipendenze di una code base da sottoporre ad analisi. Per far funzionare il nostro progetto installare installare un virtual enviroment (venv) con:
```
requests
textual
rich
pipdeptree
scancode-toolkit (se non funziona provate il bianrio)
```
gli import relativi funzionano solo quando viene eseguito come modulo, per runnarlo senza installarlo tramite il wheel fate

```
python -m license_hierarchy.licensehierarchy
```

## Architettura a Strati (Onion Architecture)

Il programma segue un'architettura a cipolla (onion architecture) con **4 strati concentrici**:

```
┌─────────────────────────────────────────┐
│         INTERFACE (Interfaccia)         │
│  GUI, Controller, Presentazione dati    │ UI
└─────────────┬───────────────────────────┘
              │ 
┌─────────────▼───────────────────────────┐
│     INFRASTRUCTURE (Infrastruttura)     │
│  HTTP, file system, processi, logging   │ I/O del programma
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│         ANALYZER (Analisi)              │
│  Logica di business, orchestrazione     │ Logica del programma
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│       ENTITIES (Entità di Dominio)      │
│  Modelli, interfacce astratte           │ 
└─────────────────────────────────────────┘


```

Tale architettura segue quindi le seguenti regole di dipendenza

-  Ogni strato **può** dipendere solo dagli strati **interni** (più vicini al centro)
-  Ogni strato **non può** dipendere dagli strati **esterni** (più lontani dal centro)
-  Utilizzo di **Dependency Injection** per preservare l'indipendenza tra i layer
  
## Struttura di packages e moduli

```
src/license_hierarchy
├── entities/                           # Strato 1: Dominio e Astrazioni
│   ├── pypi_metadata.py                # Contenitore metadati PyPI
│   ├── scan_engine.py                  # Interfaccia per scanner di licenze
│   ├── package_manager_fetcher.py      # Interfaccia client per package repository 
│   ├── abstract_dep_tree_builder.py    # Interfaccia costruttore albero dipendenze
│   ├── abstract_license_comparator.py  # Interfaccia comparatore licenze
│   └── abstract_repo_downloader.py     # Interfaccia downloader di repository (source code)
│
├── analyzer/                           # Strato 2: Logica di Business
│   ├── package_metadata_fetcher.py     # Orchestratore principale
│   ├── license_name_normalizer.py      # Normalizza nomi licenze (nome esteso-> abbreviazione)
│   ├── license_comparator.py           # Confronta licenze PyPI vs ScanCode
│   ├── tree_license_analyzer.py        # Analizza albero dipendenze per licenze
│   └── matrix_manager.py               # Gestisce matrice (file json) compatibilità licenze
│
├── infrastructure/                     # Strato 3: Infrastruttura
│   ├── pypi_client.py                  # Client HTTP per API PyPI (implementazione)
│   ├── dep_tree_builder.py             # Costruisce albero dipendenze (implementazione)
│   ├── repo_downloader.py              # Scarica repository sorgenti (implementazione)
│   ├── scancode_runner.py              # Esegue ScanCode per analisi licenze
│   ├── connectivity.py                 # Gestisce I/O (download, cache)
│   └── logger_formatter.py             # Configurazione logging
│
├── interface/                          # Strato 4: Interfaccia Utente
│   ├── gui.py                          # Interfaccia grafica (Textual)
│   ├── controller.py                   # Controller principale UI
│   ├── ui_state.py                     # Gestione stato UI
│   └── style.css                       # Stili UI
│
└────── licensehierarchy.py              # Entrypoint
```

## Flusso di Esecuzione Principale

LicenseHierarchy è uno strumento che analizza le dipendenze Python di un progetto e verifica la compatibilità delle loro licenze. Il programma:

1. **Legge** un file `requirements.txt`
2. **Costruisce** un albero completo delle dipendenze (incluse le sub-dipendenze)
3. **Recupera** i metadati delle licenze da PyPI
4. **Analizza** la compatibilità gerarchica delle licenze presenti nell'albero (usando  matrice di compatibilità)
5. **Scarica** i codici sorgente dai repository
6. **Analizza** i file con ScanCode per estrarre le licenze effettive
7. **Confronta** le licenze dichiarate su PyPI con quelle rilevate nei sorgenti



### Sequenza di Alto Livello

```
START
  │
  ├─►L'utente inserisce il path ai requirements.txt e la licenza del
  |  progetto da analizzare (Root). Durante l'inserimento della licenza
  |  verrà scaricate il file matrix.json tramite la classe 
  |  LicenseCompatibilityAnalyzer (da fare refactoring di sta classe)
  │
  |
  ├─► Il controller avvia un "retrieval" invocando il 
  |   metodo build_package_metadata dalla classe
  |   orchestratirce PackageMetadataFetcher
  |
  ├─► Quest'ultimo effettua la costruzione dell'albero
  |   delle dipendenze tramite creazione di un
  |   venv temporaneo per l'installazione ricorsiva
  |   di tutte le dipendenze  transitive tramite
  |   la classe dep_tree_builder.py (che a sua
  |   volta si basa sullo strumento pipdeptree)
  │   
  |
  ├─► Successivamente l'orchestratore effettua
  |   il recupero dei metadati da PyPI: (con cache)
  │   - package_name
  │   - license_type (dichiarata su PyPI)
  │   - repository_link
  |   tramite l'ausilio della classe pypi_client.py
  │
  |
  ├─► A questo punto l'orchestratore evocato dal controller 
  |   termina e viene eseguita una scansione di compatibilità
  |   tra le licenze dell'albero tramite la classe TreeAnalyzer
  |   che ritornerà una lista di incompatible_edges 
  |   
  |
  ├─► Confronto licenze PyPI licenses vs. ScanCode licenses
  |    Dalla TUI l'utente potrà decidere di effettuare una 
  |    analisi tramite ScanCode (opzionale). Il controller delegherà
  |    il download dei repository sorgenti alla classe repo_downloader.py
  |    tramite il metodo wrapper PackageMetadataFetcher.download_sources()
  |    Estrae licenze dal codice sorgente 
  │
  │
  └─► Output risultati
      - Discrepanze PyPI/ScanCode
      - Incompatibilità licenze
      - Report grafico
```


## Descrizione Dettagliata dei Moduli. 
### 4️⃣ ENTITIES (Strato di Dominio)

#### `pypi_metadata.py`

Contenitore per i metadati di un pacchetto scaricati da PyPI.

```python
class PyPIMetadata:
    - package: str              # Nome pacchetto
    - license_type: Optional[str]   # Licenza dichiarata su PyPI
    - link: Optional[str]       # Link repository/homepage
```

**Responsabilità:**
- Validazione non-nullità di `package`
- Accesso tramite properties con setter validati
- Immutabilità relativa ai dati di dominio

---

#### `abstract_*.py` (Classi Astratte)

Definiscono interfacce e contratti che vengono implementati negli strati superiori:

| Classe Astratta | Scopo |
|---|---|
| `AbstractPackageManagerFetcher` | Interfaccia per client package manager (PyPI, npm, ecc.) |
| `AbstractDepTreeBuilder` | Costruisce albero dipendenze in formato Dict |
| `AbstractRepoDownloader` | Scarica/estrae repository |
| `AbstractLicenseComparator` | Confronta due insiemi di licenze |

---

### 3️⃣ ANALYZER (Strato di Logica di Business)

#### `package_metadata_fetcher.py` - Orchestratore Principale

**Flusso principale: `build_package_metadata()`**

1. **Parsing requirements.txt**
   ```
   Legge il file e estrae nomi pacchetti
   ```

2. **Costruzione albero dipendenze**
   ```
   Delega a DepTreeBuilder:
   - Crea venv temporanea
   - Installa pipdeptree
   - Esegue pipdeptree per JSON output
   - Trasforma JSON → Dict[str, List[str]]
   ```

3. **Recupero metadati PyPI**
   ```
   Prende il flat set di tutte le dipendenze
   Per ciascuna:
   - Controlla cache metadata_cache.json
   - Se non in cache: delega a PyPiHandler
   - Salva in cache
   ```

4. **Costruzione oggetti PyPIMetadata**
   ```
   Per ogni pacchetto crea:
   PyPIMetadata(
       package="requests",
       license_type="Apache-2.0",
       link="https://github.com/psf/requests"
   )
   ```

**Caching:**
- Legge/scrive `data/metadata_cache.json`
- Evita richieste HTTP ripetute
- Parametro `override_cache` forza riscaricarimento

---

#### `license_comparator.py`

Confronta due insiemi di licenze: PyPI vs. ScanCode.

**Metodo principale: `compare_license_trees()`**

```
tree_a = licenze dichiarate su PyPI (da PyPIMetadata)
tree_b = licenze rilevate da ScanCode (dal codice sorgente)

Per ogni pacchetto:
  - Normalizza nomi licenze (MIT → MIT, Apache 2.0 → Apache-2.0)
  - Confronta tree_a con tree_b
  - Segna discrepanze/dubbi

Output:
  - doubts: discrepanze tra PyPI e ScanCode
  - incompatibilities: coppie licenze incompatibili nel grafo
```

---

#### `matrix_manager.py`

Gestisce la matrice di compatibilità e verifica conflitti.

**Componenti:**

1. **`CompatibilityCalcStrategy`** (Pattern Strategy)
   ```
   Interfaccia per algoritmi di calcolo compatibilità
   ```

2. **`FullCompatibilityCalc`**
   ```
   Controlla ogni coppia unica di licenze
   ```

3. **`LicenseCompatibilityAnalyzer`**
   ```
   Carica matrix.json
   Verifica compatibilità tra coppie di licenze
   Usa strategy per calcolo
   ```

**Matrice JSON (`data/matrix.json`):**
```json
{
  "MIT": {
    "Apache-2.0": "Yes",
    "GPL-3.0": "No",
    ...
  },
  ...
}
```

---

#### `tree_license_analyzer.py`

Analizza l'albero delle dipendenze e raccoglie licenze.

```python
def analyze_tree(graph: Dict[str, List[str]],
                 metadata: Dict[str, str]) -> Dict[str, str]:
    """
    Itera il grafo e costruisce mappa package → licenza
    """
```

---

### 2️⃣ INFRASTRUCTURE (Strato di Infrastruttura)

#### `pypi_client.py` - Client PyPI

Implementazione concreta di `AbstractPackageManagerFetcher`.

**Metodo principale: `get_source_links()`**

```python
def get_source_links(packages_names: List[str]) 
    → Dict[str, Dict[str, Optional[str]]]:
    """
    Input: ["requests", "numpy", ...]
    
    Output: {
        "requests": {
            "license": "Apache-2.0",
            "link": "https://github.com/psf/requests"
        },
        "numpy": {...},
        ...
    }
    """
```

**Implementazione:**
- Usa asyncio per richieste parallele
- ThreadPoolExecutor per concorrenza
- Fallback se event loop già in esecuzione
- Timeout HTTP configurabile

**Endpoint PyPI:**
```
https://pypi.org/pypi/{package_name}/json
```

---

#### `dep_tree_builder.py` - Costruttore Albero Dipendenze

Implementazione concreta di `AbstractDepTreeBuilder`.

**Flusso:**

1. **Creazione venv temporanea**
   ```
   python -m venv tmpvenv/
   ```

2. **Installazione pipdeptree**
   ```
   pip install pipdeptree
   ```

3. **Installazione dipendenze**
   ```
   pip install -r requirements.txt
   ```

4. **Esecuzione pipdeptree**
   ```
   pipdeptree --json > tree.json
   ```

5. **Parsing JSON**
   ```
   Trasforma output pipdeptree
   JSON → Dict[str, List[str]]
   
   Esempio:
   {
       "requests": ["urllib3", "certifi"],
       "urllib3": ["ssl"],
       ...
   }
   ```

**Metodi chiave:**
- `venv_exists()` - Verifica esistenza venv
- `create_venv()` - Crea venv (con opzione force_recreate)
- `delete_venv()` - Elimina venv
- `build_tree()` - Orchestra intero flusso

**Note importanti:**
- Crea venv temporanea per isolamento
- pipdeptree installa le dipendenze e costruisce albero completo
- Cross-platform: gestisce `Scripts/` (Windows) vs `bin/` (Unix)

---

#### `repo_downloader.py` - Download Repository

Implementazione concreta di `AbstractRepoDownloader`.

**Funzionalità:**
- Clona repository da GitHub/GitLab
- Estrae ZIP file
- Salva in `tmpvenv/repo_downloads/`

**Metodi:**
```python
def download_repository(url: str, output_dir: Path) → Path:
    """Scarica repo da URL, estrae ZIP"""

def extract_zip(zip_path: Path, output_dir: Path) → Path:
    """Estrae ZIP in directory"""
```

---

#### `scancode_runner.py`

Esegue ScanCode per estrarre licenze dal codice sorgente.

**Flusso:**
1. Esegue: `scancode-toolkit <repo_dir> --json`
2. Parsa output JSON
3. Estrae licenze rilevate file-by-file

**Output:**
```
Dict[file_path] → List[detected_licenses]
```

---

#### `connectivity.py`

Gestisce connessioni, cache e I/O.

**Responsabilità:**
- Download file (con timeout/retry)
- Gestione cache
- Lettura/scrittura JSON

---

#### `logger_formatter.py`

Configurazione centralizzata del logging.

```python
def initialize(name: str, level: int) → Logger:
    """Crea logger con formato standardizzato"""
```

---

### 1️⃣ INTERFACE (Strato di Presentazione)

#### `gui.py` - Viewer

Costruita con **Textual** (TUI framework).



**Widget principali:**
- `Input` - Path requirements.txt
- `Select` - Selezione licenza main
- `Tree` - Albero dipendenze
- `DataTable` - Tabella metadati
- `TabbedContent` - Tab risultati
- `Log` - Console logging
- `LoadingIndicator` - Indicatore progresso

**Gestione asincrona:**
- Analisi eseguita in background
- UI responsiva con asyncio
- `TextualLogHandler` invia log dalla UI

---

#### `controller.py` - Controller Principale

Orchiestra la comunicazione GUI ↔ Logica di business.

**Responsabilità:**
- Inizializza orchestratore metadata
- Esegue analisi
- Formatta risultati per UI
- Gestisce comandi utente

**Metodi principali:**
```python
def initialize_matrix() → None:
    """Carica matrice compatibilità"""

def analyze_requirements(path: str) → None:
    """Avvia analisi dependencies"""

def check_compatibility() → None:
    """Verifica compatibilità licenze"""
```

---

#### `ui_state.py`

Enumerazioni e stato UI.

```python
class Stage(Enum):
    READY, ANALYZING, COMPLETE

class SuggestionState(Enum):
    SCANNING, CACHED, DOWNLOADED
```




## Componenti di Infrastruttura

### Dependency Injection

L'analyzer non può importare direttamente da infrastructure per preservare onion architecture. Quindi:

```python
# In analyzer/package_metadata_fetcher.py
class PackageMetadataFetcher:
    def __init__(self,
                 pypi_client: AbstractPackageManagerFetcher,  # ← injected
                 dep_builder: AbstractDepTreeBuilder,        # ← injected
                 repo_downloader: AbstractRepoDownloader):   # ← injected
        self.pypi_client = pypi_client
        self.dep_builder = dep_builder
        self.repo_downloader = repo_downloader
```

Nel main (interface layer) si iniettano le implementazioni concrete:

```python
# In analyzer/main.py or interface/controller.py
pypi_client_instance = pypi_client.PyPiHandler()
dep_tree_builder_instance = dep_tree_builder.DepTreeBuilder()
repo_downloader_instance = repo_downloader.RepoDownloader()

orchestrator = PackageMetadataFetcher(
    pypi_client_instance,
    dep_tree_builder_instance,
    repo_downloader_instance
)
```

### Directory Temporanea

```
tmpvenv/
├── pyvenv.cfg           # Configurazione venv
├── Include/             # Header C
├── Lib/
│   └── site-packages/   # Pacchetti installati
├── Scripts/             # (Windows) Eseguibili
├── bin/                 # (Unix) Eseguibili
└── repo_downloads/      # Repository scaricati
```

### Cache

```
data/
├── matrix.json          # Matrice compatibilità (da web o locale)
└── metadata_cache.json  # Cache PyPI metadata
```

---

