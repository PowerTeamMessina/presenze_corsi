import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
import hashlib
import secrets


# ============================================================
# CONFIGURAZIONE
# ============================================================

st.set_page_config(
    page_title="Statino Corsi Nuoto",
    page_icon="🏊",
    layout="wide"
)

DB_NAME = "corsi_nuoto.db"


# ============================================================
# DATABASE
# ============================================================

conn = sqlite3.connect(
    DB_NAME,
    check_same_thread=False
)

c = conn.cursor()


# ============================================================
# FUNZIONI PASSWORD
# ============================================================

def hash_password(password, salt=None):

    if salt is None:
        salt = secrets.token_hex(16)

    password_hash = hashlib.sha256(
        (password + salt).encode("utf-8")
    ).hexdigest()

    return password_hash, salt


def verifica_password(password_inserita, password_hash, salt):

    nuovo_hash, _ = hash_password(
        password_inserita,
        salt
    )

    return nuovo_hash == password_hash


# ============================================================
# TABELLE
# ============================================================

c.execute("""
CREATE TABLE IF NOT EXISTS utenti (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    nome TEXT NOT NULL,
    ruolo TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    attivo INTEGER DEFAULT 1
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS corsi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    livello TEXT,
    giorno TEXT,
    orario TEXT,
    stagione TEXT,
    attivo INTEGER DEFAULT 1
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS bambini (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    cognome TEXT NOT NULL,
    data_nascita TEXT,
    corso_id INTEGER NOT NULL,
    note TEXT,
    attivo INTEGER DEFAULT 1,
    FOREIGN KEY(corso_id) REFERENCES corsi(id)
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS assegnazioni_istruttori (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    istruttore_id INTEGER NOT NULL,
    corso_id INTEGER NOT NULL,
    data_specifica TEXT,
    attiva INTEGER DEFAULT 1,
    FOREIGN KEY(istruttore_id) REFERENCES utenti(id),
    FOREIGN KEY(corso_id) REFERENCES corsi(id)
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS presenze (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bambino_id INTEGER NOT NULL,
    corso_id INTEGER NOT NULL,
    data TEXT NOT NULL,
    presenza INTEGER NOT NULL,
    note TEXT,
    inserito_da INTEGER,
    UNIQUE(
        bambino_id,
        corso_id,
        data
    ),
    FOREIGN KEY(bambino_id) REFERENCES bambini(id),
    FOREIGN KEY(corso_id) REFERENCES corsi(id),
    FOREIGN KEY(inserito_da) REFERENCES utenti(id)
)
""")

conn.commit()


# ============================================================
# CREAZIONE MANAGER DEFAULT
# ============================================================

def crea_manager_default():

    df = pd.read_sql(
        """
        SELECT *
        FROM utenti
        WHERE ruolo = 'manager'
        """,
        conn
    )

    if df.empty:

        username = st.secrets.get(
            "MANAGER_USERNAME",
            "editor"
        )

        password = st.secrets.get(
            "MANAGER_PASSWORD",
            "pattern95@"
        )

        password_hash, salt = hash_password(password)

        c.execute(
            """
            INSERT INTO utenti(
                username,
                nome,
                ruolo,
                password_hash,
                salt,
                attivo
            )
            VALUES(?,?,?,?,?,1)
            """,
            (
                username,
                "Manager",
                "manager",
                password_hash,
                salt
            )
        )

        conn.commit()


crea_manager_default()


# ============================================================
# FUNZIONI UTENTI
# ============================================================

def get_utenti():

    return pd.read_sql(
        """
        SELECT
            id,
            username,
            nome,
            ruolo,
            attivo
        FROM utenti
        ORDER BY ruolo, nome
        """,
        conn
    )


def get_istruttori(attivi_solo=True):

    query = """
        SELECT
            id,
            username,
            nome,
            ruolo,
            attivo
        FROM utenti
        WHERE ruolo = 'istruttore'
    """

    if attivi_solo:
        query += " AND attivo = 1"

    query += " ORDER BY nome"

    return pd.read_sql(
        query,
        conn
    )


def aggiungi_istruttore(username, nome, password):

    password_hash, salt = hash_password(password)

    c.execute(
        """
        INSERT INTO utenti(
            username,
            nome,
            ruolo,
            password_hash,
            salt,
            attivo
        )
        VALUES(?,?,?,?,?,1)
        """,
        (
            username,
            nome,
            "istruttore",
            password_hash,
            salt
        )
    )

    conn.commit()


def aggiorna_password_utente(utente_id, nuova_password):

    password_hash, salt = hash_password(nuova_password)

    c.execute(
        """
        UPDATE utenti
        SET password_hash = ?,
            salt = ?
        WHERE id = ?
        """,
        (
            password_hash,
            salt,
            utente_id
        )
    )

    conn.commit()


def cambia_stato_utente(utente_id, attivo):

    c.execute(
        """
        UPDATE utenti
        SET attivo = ?
        WHERE id = ?
        """,
        (
            int(attivo),
            utente_id
        )
    )

    conn.commit()


def login():

    st.sidebar.header("🔐 Login")

    if "utente_id" not in st.session_state:
        st.session_state.utente_id = None

    if "username" not in st.session_state:
        st.session_state.username = None

    if "nome_utente" not in st.session_state:
        st.session_state.nome_utente = None

    if "ruolo" not in st.session_state:
        st.session_state.ruolo = None

    if st.session_state.utente_id is not None:

        st.sidebar.success(
            f"Accesso: {st.session_state.nome_utente}"
        )

        st.sidebar.write(
            f"Ruolo: {st.session_state.ruolo}"
        )

        if st.sidebar.button("🚪 Logout"):

            st.session_state.utente_id = None
            st.session_state.username = None
            st.session_state.nome_utente = None
            st.session_state.ruolo = None

            st.rerun()

        return

    username = st.sidebar.text_input(
        "Username"
    )

    password = st.sidebar.text_input(
        "Password",
        type="password"
    )

    if st.sidebar.button("Accedi"):

        utente = pd.read_sql(
            """
            SELECT *
            FROM utenti
            WHERE username = ?
            AND attivo = 1
            """,
            conn,
            params=(username,)
        )

        if utente.empty:

            st.sidebar.error(
                "Credenziali non valide."
            )

            return

        row = utente.iloc[0]

        ok = verifica_password(
            password,
            row["password_hash"],
            row["salt"]
        )

        if ok:

            st.session_state.utente_id = int(row["id"])
            st.session_state.username = row["username"]
            st.session_state.nome_utente = row["nome"]
            st.session_state.ruolo = row["ruolo"]

            st.rerun()

        else:

            st.sidebar.error(
                "Credenziali non valide."
            )


def is_manager():

    return st.session_state.get("ruolo") == "manager"


def is_istruttore():

    return st.session_state.get("ruolo") == "istruttore"


def is_loggato():

    return st.session_state.get("utente_id") is not None


# ============================================================
# FUNZIONI CORSI
# ============================================================

def get_corsi(attivi_solo=True):

    query = """
        SELECT *
        FROM corsi
    """

    if attivi_solo:
        query += " WHERE attivo = 1"

    query += """
        ORDER BY stagione, giorno, orario, nome
    """

    return pd.read_sql(
        query,
        conn
    )


def get_corso_by_id(corso_id):

    return pd.read_sql(
        """
        SELECT *
        FROM corsi
        WHERE id = ?
        """,
        conn,
        params=(corso_id,)
    )


def aggiungi_corso(nome, livello, giorno, orario, stagione):

    c.execute(
        """
        INSERT INTO corsi(
            nome,
            livello,
            giorno,
            orario,
            stagione,
            attivo
        )
        VALUES(?,?,?,?,?,1)
        """,
        (
            nome,
            livello,
            giorno,
            orario,
            stagione
        )
    )

    conn.commit()


def aggiorna_corso(corso_id, nome, livello, giorno, orario, stagione, attivo):

    c.execute(
        """
        UPDATE corsi
        SET nome = ?,
            livello = ?,
            giorno = ?,
            orario = ?,
            stagione = ?,
            attivo = ?
        WHERE id = ?
        """,
        (
            nome,
            livello,
            giorno,
            orario,
            stagione,
            int(attivo),
            corso_id
        )
    )

    conn.commit()


def elimina_corso(corso_id):

    c.execute(
        """
        DELETE FROM presenze
        WHERE corso_id = ?
        """,
        (corso_id,)
    )

    c.execute(
        """
        DELETE FROM bambini
        WHERE corso_id = ?
        """,
        (corso_id,)
    )

    c.execute(
        """
        DELETE FROM assegnazioni_istruttori
        WHERE corso_id = ?
        """,
        (corso_id,)
    )

    c.execute(
        """
        DELETE FROM corsi
        WHERE id = ?
        """,
        (corso_id,)
    )

    conn.commit()


# ============================================================
# FUNZIONI ASSEGNAZIONI
# ============================================================

def assegna_istruttore(istruttore_id, corso_id, data_specifica=None):

    if data_specifica == "":
        data_specifica = None

    c.execute(
        """
        INSERT INTO assegnazioni_istruttori(
            istruttore_id,
            corso_id,
            data_specifica,
            attiva
        )
        VALUES(?,?,?,1)
        """,
        (
            istruttore_id,
            corso_id,
            data_specifica
        )
    )

    conn.commit()


def get_assegnazioni():

    return pd.read_sql(
        """
        SELECT
            ai.id,
            u.nome AS istruttore,
            c.nome AS corso,
            c.giorno,
            c.orario,
            ai.data_specifica,
            ai.attiva
        FROM assegnazioni_istruttori ai
        JOIN utenti u
            ON u.id = ai.istruttore_id
        JOIN corsi c
            ON c.id = ai.corso_id
        ORDER BY u.nome, c.nome, ai.data_specifica
        """,
        conn
    )


def elimina_assegnazione(assegnazione_id):

    c.execute(
        """
        DELETE FROM assegnazioni_istruttori
        WHERE id = ?
        """,
        (assegnazione_id,)
    )

    conn.commit()


def istruttore_abilitato_corso_data(istruttore_id, corso_id, data_evento):

    data_str = str(data_evento)

    df = pd.read_sql(
        """
        SELECT *
        FROM assegnazioni_istruttori
        WHERE istruttore_id = ?
        AND corso_id = ?
        AND attiva = 1
        AND (
            data_specifica IS NULL
            OR data_specifica = ?
        )
        """,
        conn,
        params=(
            istruttore_id,
            corso_id,
            data_str
        )
    )

    return not df.empty


def get_corsi_visibili_per_utente(data_evento=None):

    if is_manager():

        return get_corsi(attivi_solo=True)

    if is_istruttore():

        istruttore_id = st.session_state.utente_id

        if data_evento is None:

            return pd.read_sql(
                """
                SELECT DISTINCT c.*
                FROM corsi c
                JOIN assegnazioni_istruttori ai
                    ON ai.corso_id = c.id
                WHERE ai.istruttore_id = ?
                AND ai.attiva = 1
                AND c.attivo = 1
                ORDER BY c.giorno, c.orario, c.nome
                """,
                conn,
                params=(istruttore_id,)
            )

        return pd.read_sql(
            """
            SELECT DISTINCT c.*
            FROM corsi c
            JOIN assegnazioni_istruttori ai
                ON ai.corso_id = c.id
            WHERE ai.istruttore_id = ?
            AND ai.attiva = 1
            AND c.attivo = 1
            AND (
                ai.data_specifica IS NULL
                OR ai.data_specifica = ?
            )
            ORDER BY c.giorno, c.orario, c.nome
            """,
            conn,
            params=(
                istruttore_id,
                str(data_evento)
            )
        )

    return pd.DataFrame()


# ============================================================
# FUNZIONI BAMBINI
# ============================================================

def get_bambini_corso(corso_id, attivi_solo=True):

    query = """
        SELECT *
        FROM bambini
        WHERE corso_id = ?
    """

    if attivi_solo:
        query += " AND attivo = 1"

    query += " ORDER BY cognome, nome"

    return pd.read_sql(
        query,
        conn,
        params=(corso_id,)
    )


def aggiungi_bambino(nome, cognome, data_nascita, corso_id, note):

    c.execute(
        """
        INSERT INTO bambini(
            nome,
            cognome,
            data_nascita,
            corso_id,
            note,
            attivo
        )
        VALUES(?,?,?,?,?,1)
        """,
        (
            nome,
            cognome,
            str(data_nascita) if data_nascita else "",
            corso_id,
            note
        )
    )

    conn.commit()


def aggiorna_bambino(bambino_id, nome, cognome, data_nascita, note, attivo):

    c.execute(
        """
        UPDATE bambini
        SET nome = ?,
            cognome = ?,
            data_nascita = ?,
            note = ?,
            attivo = ?
        WHERE id = ?
        """,
        (
            nome,
            cognome,
            str(data_nascita) if data_nascita else "",
            note,
            int(attivo),
            bambino_id
        )
    )

    conn.commit()


def elimina_bambino(bambino_id):

    c.execute(
        """
        DELETE FROM presenze
        WHERE bambino_id = ?
        """,
        (bambino_id,)
    )

    c.execute(
        """
        DELETE FROM bambini
        WHERE id = ?
        """,
        (bambino_id,)
    )

    conn.commit()


# ============================================================
# FUNZIONI PRESENZE
# ============================================================

def get_presenze_corso_data(corso_id, data_evento):

    return pd.read_sql(
        """
        SELECT *
        FROM presenze
        WHERE corso_id = ?
        AND data = ?
        """,
        conn,
        params=(
            corso_id,
            str(data_evento)
        )
    )


def salva_presenza(bambino_id, corso_id, data_evento, presenza, note):

    c.execute(
        """
        INSERT INTO presenze(
            bambino_id,
            corso_id,
            data,
            presenza,
            note,
            inserito_da
        )
        VALUES(?,?,?,?,?,?)

        ON CONFLICT(
            bambino_id,
            corso_id,
            data
        )

        DO UPDATE SET
            presenza = excluded.presenza,
            note = excluded.note,
            inserito_da = excluded.inserito_da
        """,
        (
            bambino_id,
            corso_id,
            str(data_evento),
            int(presenza),
            note,
            st.session_state.utente_id
        )
    )

    conn.commit()


def storico_presenze():

    return pd.read_sql(
        """
        SELECT
            p.data,
            c.nome AS corso,
            c.giorno,
            c.orario,
            b.cognome,
            b.nome,
            p.presenza,
            p.note,
            u.nome AS inserito_da
        FROM presenze p
        JOIN bambini b
            ON b.id = p.bambino_id
        JOIN corsi c
            ON c.id = p.corso_id
        LEFT JOIN utenti u
            ON u.id = p.inserito_da
        ORDER BY p.data DESC, c.nome, b.cognome, b.nome
        """,
        conn
    )


# ============================================================
# INTERFACCIA
# ============================================================

st.title("🏊 Statino Presenze Corsi di Nuoto")

login()

if not is_loggato():

    st.info(
        "Effettua il login per accedere al gestionale."
    )

    st.stop()


st.markdown(
    f"""
    **Utente:** {st.session_state.nome_utente}  
    **Ruolo:** {st.session_state.ruolo}
    """
)


# ============================================================
# TAB
# ============================================================

if is_manager():

    tabs = st.tabs(
        [
            "📋 Presenze",
            "👶 Bambini",
            "🏊 Corsi",
            "👨‍🏫 Istruttori",
            "🔗 Assegnazioni",
            "🗂️ Storico"
        ]
    )

    tab_presenze = tabs[0]
    tab_bambini = tabs[1]
    tab_corsi = tabs[2]
    tab_istruttori = tabs[3]
    tab_assegnazioni = tabs[4]
    tab_storico = tabs[5]

else:

    tabs = st.tabs(
        [
            "📋 Presenze",
            "👶 Bambini",
            "🗂️ Storico personale"
        ]
    )

    tab_presenze = tabs[0]
    tab_bambini = tabs[1]
    tab_storico = tabs[2]


# ============================================================
# TAB PRESENZE
# ============================================================

with tab_presenze:

    st.header("📋 Registro presenze")

    data_evento = st.date_input(
        "Data",
        value=date.today(),
        key="data_presenze"
    )

    corsi_visibili = get_corsi_visibili_per_utente(
        data_evento
    )

    if corsi_visibili.empty:

        st.warning(
            "Non hai corsi disponibili per questa data."
        )

    else:

        opzioni_corsi = {
            f"{row['nome']} | {row['giorno']} | {row['orario']}": int(row["id"])
            for _, row in corsi_visibili.iterrows()
        }

        corso_label = st.selectbox(
            "Corso",
            list(opzioni_corsi.keys()),
            key="corso_presenze"
        )

        corso_id = opzioni_corsi[corso_label]

        if is_istruttore():

            abilitato = istruttore_abilitato_corso_data(
                st.session_state.utente_id,
                corso_id,
                data_evento
            )

            if not abilitato:

                st.error(
                    "Non sei abilitato a compilare questo corso in questa data."
                )

                st.stop()

        bambini = get_bambini_corso(
            corso_id,
            attivi_solo=True
        )

        if bambini.empty:

            st.info(
                "Nessun bambino inserito in questo corso."
            )

        else:

            presenze_salvate = get_presenze_corso_data(
                corso_id,
                data_evento
            )

            dati_salvati = {}

            for _, r in presenze_salvate.iterrows():

                dati_salvati[int(r["bambino_id"])] = {
                    "presenza": bool(r["presenza"]),
                    "note": r["note"] if pd.notna(r["note"]) else ""
                }

            st.markdown("---")

            presenti = 0
            registro = {}

            for _, b in bambini.iterrows():

                bambino_id = int(b["id"])

                default_presenza = dati_salvati.get(
                    bambino_id,
                    {}
                ).get(
                    "presenza",
                    False
                )

                default_note = dati_salvati.get(
                    bambino_id,
                    {}
                ).get(
                    "note",
                    ""
                )

                st.subheader(
                    f"{b['cognome']} {b['nome']}"
                )

                col1, col2 = st.columns(
                    [1, 3]
                )

                presenza = col1.toggle(
                    "Presente",
                    value=default_presenza,
                    key=f"pres_{corso_id}_{data_evento}_{bambino_id}"
                )

                note = col2.text_input(
                    "Note",
                    value=default_note,
                    key=f"note_{corso_id}_{data_evento}_{bambino_id}"
                )

                if presenza:
                    presenti += 1

                registro[bambino_id] = {
                    "presenza": presenza,
                    "note": note
                }

                st.markdown("---")

            assenti = len(bambini) - presenti

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "Iscritti",
                len(bambini)
            )

            c2.metric(
                "Presenti",
                presenti
            )

            c3.metric(
                "Assenti",
                assenti
            )

            if st.button(
                "💾 Salva presenze",
                key="salva_presenze"
            ):

                for bambino_id, dati in registro.items():

                    salva_presenza(
                        bambino_id,
                        corso_id,
                        data_evento,
                        dati["presenza"],
                        dati["note"]
                    )

                st.success(
                    "Presenze salvate correttamente."
                )

                st.rerun()


# ============================================================
# TAB BAMBINI
# ============================================================

with tab_bambini:

    st.header("👶 Gestione bambini")

    corsi_visibili = get_corsi_visibili_per_utente()

    if corsi_visibili.empty:

        st.warning(
            "Non hai corsi assegnati."
        )

    else:

        opzioni_corsi = {
            f"{row['nome']} | {row['giorno']} | {row['orario']}": int(row["id"])
            for _, row in corsi_visibili.iterrows()
        }

        corso_label = st.selectbox(
            "Corso",
            list(opzioni_corsi.keys()),
            key="corso_bambini"
        )

        corso_id = opzioni_corsi[corso_label]

        st.subheader("➕ Aggiungi bambino")

        with st.form(
            "form_aggiungi_bambino",
            clear_on_submit=True
        ):

            nome = st.text_input(
                "Nome"
            )

            cognome = st.text_input(
                "Cognome"
            )

            data_nascita = st.date_input(
                "Data di nascita",
                value=None
            )

            note = st.text_area(
                "Note"
            )

            invia = st.form_submit_button(
                "➕ Aggiungi"
            )

            if invia:

                if nome.strip() == "" or cognome.strip() == "":

                    st.error(
                        "Nome e cognome sono obbligatori."
                    )

                else:

                    aggiungi_bambino(
                        nome.strip(),
                        cognome.strip(),
                        data_nascita,
                        corso_id,
                        note.strip()
                    )

                    st.success(
                        "Bambino aggiunto correttamente."
                    )

                    st.rerun()

        st.markdown("---")

        st.subheader("📋 Elenco bambini")

        bambini = get_bambini_corso(
            corso_id,
            attivi_solo=False if is_manager() else True
        )

        if bambini.empty:

            st.info(
                "Nessun bambino presente in questo corso."
            )

        else:

            st.dataframe(
                bambini[
                    [
                        "id",
                        "cognome",
                        "nome",
                        "data_nascita",
                        "note",
                        "attivo"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

            if is_manager():

                st.markdown("---")

                st.subheader("✏️ Modifica o elimina bambino")

                opzioni_bambini = {
                    f"{row['cognome']} {row['nome']}": int(row["id"])
                    for _, row in bambini.iterrows()
                }

                bambino_label = st.selectbox(
                    "Bambino",
                    list(opzioni_bambini.keys()),
                    key="modifica_bambino"
                )

                bambino_id = opzioni_bambini[bambino_label]

                dati = bambini[
                    bambini["id"] == bambino_id
                ].iloc[0]

                nuovo_nome = st.text_input(
                    "Nome",
                    value=dati["nome"],
                    key="nuovo_nome_bambino"
                )

                nuovo_cognome = st.text_input(
                    "Cognome",
                    value=dati["cognome"],
                    key="nuovo_cognome_bambino"
                )

                nuova_data = st.text_input(
                    "Data nascita",
                    value=dati["data_nascita"] if pd.notna(dati["data_nascita"]) else "",
                    key="nuova_data_bambino"
                )

                nuove_note = st.text_area(
                    "Note",
                    value=dati["note"] if pd.notna(dati["note"]) else "",
                    key="nuove_note_bambino"
                )

                nuovo_attivo = st.checkbox(
                    "Attivo",
                    value=bool(dati["attivo"]),
                    key="attivo_bambino"
                )

                if st.button(
                    "💾 Aggiorna bambino"
                ):

                    aggiorna_bambino(
                        bambino_id,
                        nuovo_nome.strip(),
                        nuovo_cognome.strip(),
                        nuova_data,
                        nuove_note.strip(),
                        nuovo_attivo
                    )

                    st.success(
                        "Bambino aggiornato."
                    )

                    st.rerun()

                conferma_elimina = st.checkbox(
                    "Confermo eliminazione definitiva bambino"
                )

                if st.button(
                    "🗑️ Elimina bambino"
                ):

                    if not conferma_elimina:

                        st.error(
                            "Devi confermare l'eliminazione."
                        )

                    else:

                        elimina_bambino(
                            bambino_id
                        )

                        st.success(
                            "Bambino eliminato."
                        )

                        st.rerun()


# ============================================================
# TAB CORSI
# ============================================================

if is_manager():

    with tab_corsi:

        st.header("🏊 Gestione corsi")

        st.subheader("➕ Nuovo corso")

        with st.form(
            "form_nuovo_corso",
            clear_on_submit=True
        ):

            nome = st.text_input(
                "Nome corso",
                placeholder="es. Corso Bambini 1"
            )

            livello = st.text_input(
                "Livello",
                placeholder="es. Principianti"
            )

            giorno = st.selectbox(
                "Giorno",
                [
                    "Lunedì",
                    "Martedì",
                    "Mercoledì",
                    "Giovedì",
                    "Venerdì",
                    "Sabato",
                    "Domenica"
                ]
            )

            orario = st.text_input(
                "Orario",
                placeholder="es. 16:00-17:00"
            )

            stagione = st.text_input(
                "Stagione",
                value="2026/2027"
            )

            crea = st.form_submit_button(
                "➕ Crea corso"
            )

            if crea:

                if nome.strip() == "":

                    st.error(
                        "Inserisci il nome del corso."
                    )

                else:

                    aggiungi_corso(
                        nome.strip(),
                        livello.strip(),
                        giorno,
                        orario.strip(),
                        stagione.strip()
                    )

                    st.success(
                        "Corso creato correttamente."
                    )

                    st.rerun()

        st.markdown("---")

        st.subheader("📋 Corsi presenti")

        corsi = get_corsi(
            attivi_solo=False
        )

        if corsi.empty:

            st.info(
                "Nessun corso presente."
            )

        else:

            st.dataframe(
                corsi,
                use_container_width=True,
                hide_index=True
            )

            st.markdown("---")

            st.subheader("✏️ Modifica corso")

            opzioni_corsi = {
                f"{row['nome']} | {row['giorno']} | {row['orario']}": int(row["id"])
                for _, row in corsi.iterrows()
            }

            corso_label = st.selectbox(
                "Seleziona corso",
                list(opzioni_corsi.keys()),
                key="modifica_corso"
            )

            corso_id = opzioni_corsi[corso_label]

            dati_corso = corsi[
                corsi["id"] == corso_id
            ].iloc[0]

            nuovo_nome = st.text_input(
                "Nome corso",
                value=dati_corso["nome"]
            )

            nuovo_livello = st.text_input(
                "Livello",
                value=dati_corso["livello"] if pd.notna(dati_corso["livello"]) else ""
            )

            nuovo_giorno = st.selectbox(
                "Giorno",
                [
                    "Lunedì",
                    "Martedì",
                    "Mercoledì",
                    "Giovedì",
                    "Venerdì",
                    "Sabato",
                    "Domenica"
                ],
                index=[
                    "Lunedì",
                    "Martedì",
                    "Mercoledì",
                    "Giovedì",
                    "Venerdì",
                    "Sabato",
                    "Domenica"
                ].index(dati_corso["giorno"])
                if dati_corso["giorno"] in [
                    "Lunedì",
                    "Martedì",
                    "Mercoledì",
                    "Giovedì",
                    "Venerdì",
                    "Sabato",
                    "Domenica"
                ]
                else 0
            )

            nuovo_orario = st.text_input(
                "Orario",
                value=dati_corso["orario"] if pd.notna(dati_corso["orario"]) else ""
            )

            nuova_stagione = st.text_input(
                "Stagione",
                value=dati_corso["stagione"] if pd.notna(dati_corso["stagione"]) else ""
            )

            nuovo_attivo = st.checkbox(
                "Corso attivo",
                value=bool(dati_corso["attivo"])
            )

            if st.button(
                "💾 Aggiorna corso"
            ):

                aggiorna_corso(
                    corso_id,
                    nuovo_nome.strip(),
                    nuovo_livello.strip(),
                    nuovo_giorno,
                    nuovo_orario.strip(),
                    nuova_stagione.strip(),
                    nuovo_attivo
                )

                st.success(
                    "Corso aggiornato."
                )

                st.rerun()

            conferma_elimina_corso = st.checkbox(
                "Confermo eliminazione definitiva corso"
            )

            if st.button(
                "🗑️ Elimina corso"
            ):

                if not conferma_elimina_corso:

                    st.error(
                        "Devi confermare l'eliminazione."
                    )

                else:

                    elimina_corso(
                        corso_id
                    )

                    st.success(
                        "Corso eliminato."
                    )

                    st.rerun()


# ============================================================
# TAB ISTRUTTORI
# ============================================================

if is_manager():

    with tab_istruttori:

        st.header("👨‍🏫 Gestione istruttori")

        st.subheader("➕ Nuovo istruttore")

        with st.form(
            "form_nuovo_istruttore",
            clear_on_submit=True
        ):

            username = st.text_input(
                "Username"
            )

            nome = st.text_input(
                "Nome istruttore"
            )

            password = st.text_input(
                "Password iniziale",
                type="password"
            )

            crea = st.form_submit_button(
                "➕ Crea istruttore"
            )

            if crea:

                if (
                    username.strip() == ""
                    or nome.strip() == ""
                    or password.strip() == ""
                ):

                    st.error(
                        "Compila tutti i campi."
                    )

                else:

                    try:

                        aggiungi_istruttore(
                            username.strip(),
                            nome.strip(),
                            password.strip()
                        )

                        st.success(
                            "Istruttore creato correttamente."
                        )

                        st.rerun()

                    except sqlite3.IntegrityError:

                        st.error(
                            "Username già esistente."
                        )

        st.markdown("---")

        st.subheader("📋 Istruttori")

        istruttori = get_istruttori(
            attivi_solo=False
        )

        if istruttori.empty:

            st.info(
                "Nessun istruttore presente."
            )

        else:

            st.dataframe(
                istruttori,
                use_container_width=True,
                hide_index=True
            )

            st.markdown("---")

            st.subheader("⚙️ Modifica istruttore")

            opzioni = {
                f"{row['nome']} ({row['username']})": int(row["id"])
                for _, row in istruttori.iterrows()
            }

            scelta = st.selectbox(
                "Istruttore",
                list(opzioni.keys()),
                key="istruttore_modifica"
            )

            istruttore_id = opzioni[scelta]

            dati_istruttore = istruttori[
                istruttori["id"] == istruttore_id
            ].iloc[0]

            attivo = st.checkbox(
                "Account attivo",
                value=bool(dati_istruttore["attivo"]),
                key="stato_istruttore"
            )

            if st.button(
                "💾 Aggiorna stato account"
            ):

                cambia_stato_utente(
                    istruttore_id,
                    attivo
                )

                st.success(
                    "Stato account aggiornato."
                )

                st.rerun()

            nuova_password = st.text_input(
                "Nuova password",
                type="password",
                key="nuova_password_istruttore"
            )

            if st.button(
                "🔐 Cambia password istruttore"
            ):

                if nuova_password.strip() == "":

                    st.error(
                        "Inserisci una nuova password."
                    )

                else:

                    aggiorna_password_utente(
                        istruttore_id,
                        nuova_password.strip()
                    )

                    st.success(
                        "Password aggiornata."
                    )

                    st.rerun()


# ============================================================
# TAB ASSEGNAZIONI
# ============================================================

if is_manager():

    with tab_assegnazioni:

        st.header("🔗 Assegnazione istruttori ai corsi")

        istruttori = get_istruttori(
            attivi_solo=True
        )

        corsi = get_corsi(
            attivi_solo=True
        )

        if istruttori.empty or corsi.empty:

            st.info(
                "Servono almeno un istruttore attivo e un corso attivo."
            )

        else:

            opzioni_istruttori = {
                f"{row['nome']} ({row['username']})": int(row["id"])
                for _, row in istruttori.iterrows()
            }

            opzioni_corsi = {
                f"{row['nome']} | {row['giorno']} | {row['orario']}": int(row["id"])
                for _, row in corsi.iterrows()
            }

            istruttore_label = st.selectbox(
                "Istruttore",
                list(opzioni_istruttori.keys()),
                key="assegna_istruttore"
            )

            corso_label = st.selectbox(
                "Corso",
                list(opzioni_corsi.keys()),
                key="assegna_corso"
            )

            tipo_assegnazione = st.radio(
                "Tipo assegnazione",
                [
                    "Intero corso",
                    "Solo una data specifica"
                ],
                horizontal=True
            )

            data_specifica = None

            if tipo_assegnazione == "Solo una data specifica":

                data_specifica = st.date_input(
                    "Data specifica",
                    value=date.today(),
                    key="data_specifica_assegnazione"
                )

            if st.button(
                "➕ Assegna istruttore"
            ):

                assegna_istruttore(
                    opzioni_istruttori[istruttore_label],
                    opzioni_corsi[corso_label],
                    str(data_specifica) if data_specifica else None
                )

                st.success(
                    "Assegnazione inserita."
                )

                st.rerun()

        st.markdown("---")

        st.subheader("📋 Assegnazioni presenti")

        assegnazioni = get_assegnazioni()

        if assegnazioni.empty:

            st.info(
                "Nessuna assegnazione presente."
            )

        else:

            st.dataframe(
                assegnazioni,
                use_container_width=True,
                hide_index=True
            )

            opzioni_ass = {
                f"{row['id']} | {row['istruttore']} | {row['corso']} | {row['data_specifica']}": int(row["id"])
                for _, row in assegnazioni.iterrows()
            }

            scelta_ass = st.selectbox(
                "Assegnazione da eliminare",
                list(opzioni_ass.keys()),
                key="elimina_assegnazione"
            )

            conferma = st.checkbox(
                "Confermo eliminazione assegnazione"
            )

            if st.button(
                "🗑️ Elimina assegnazione"
            ):

                if not conferma:

                    st.error(
                        "Devi confermare."
                    )

                else:

                    elimina_assegnazione(
                        opzioni_ass[scelta_ass]
                    )

                    st.success(
                        "Assegnazione eliminata."
                    )

                    st.rerun()


# ============================================================
# TAB STORICO
# ============================================================

with tab_storico:

    st.header("🗂️ Storico presenze")

    storico = storico_presenze()

    if is_istruttore():

        corsi_visibili = get_corsi_visibili_per_utente()

        ids_corsi = corsi_visibili["id"].tolist()

        storico = storico[
            storico["corso"].isin(
                corsi_visibili["nome"].tolist()
            )
        ]

    if storico.empty:

        st.info(
            "Nessuna presenza registrata."
        )

    else:

        storico["presenza"] = storico["presenza"].map(
            {
                1: "Presente",
                0: "Assente"
            }
        )

        st.dataframe(
            storico,
            use_container_width=True,
            hide_index=True
        )

        csv = storico.to_csv(
            index=False
        ).encode(
            "utf-8"
        )

        st.download_button(
            "📥 Scarica storico CSV",
            csv,
            "storico_presenze_corsi.csv",
            "text/csv"
        )
