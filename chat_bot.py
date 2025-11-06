from flask import Flask, request, jsonify, render_template
import os
import psycopg2
import PyPDF2
import requests
import chromadb
from sentence_transformers import SentenceTransformer
import sys
sys.stdout.reconfigure(encoding='utf-8')

# === CONFIGURAÇÕES ===
app = Flask(__name__)

DB_CONFIG = {
    'host': 'localhost',
    'dbname': 'postgres',
    'user': 'postgres',
    'password': 'lain',
}


GROQ_MODEL = "llama-3.3-70b-versatile"

# === Inicializa modelo de embeddings e banco vetorial Chroma ===
modelo_embeddings = SentenceTransformer("all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path="chroma_db")
colecao = chroma_client.get_or_create_collection("documentos_pdf")

# ===---------------------------------------------------------===

def get_db_conn():
    return psycopg2.connect(**DB_CONFIG)

def inicializar_banco():
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversas (
                id SERIAL PRIMARY KEY,
                usuario VARCHAR(50),
                pergunta TEXT,
                resposta TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("✨ Banco de dados inicializado.")
    except Exception as e:
        print(f"❌ Erro ao inicializar banco: {e}")

def extrair_texto_pdf(caminho_pdf):
    """Extrai texto puro de um PDF."""
    try:
        with open(caminho_pdf, "rb") as f:
            leitor = PyPDF2.PdfReader(f)
            texto = ""
            for pagina in leitor.pages:
                texto_pagina = pagina.extract_text()
                if texto_pagina:
                    texto += texto_pagina + "\n"
            return texto.strip()
    except Exception as e:
        print(f"Erro ao ler {caminho_pdf}: {e}")
        return ""

def carregar_pdfs_para_chroma(pasta="pdfs"):
    """Extrai texto dos PDFs e armazena embeddings no ChromaDB."""
    print("📂 Carregando PDFs e criando embeddings...")
    arquivos = [f for f in os.listdir(pasta) if f.lower().endswith(".pdf")]

    for nome_arquivo in arquivos:
        caminho = os.path.join(pasta, nome_arquivo)
        texto = extrair_texto_pdf(caminho)
        if not texto:
            continue

        # Quebra o texto em blocos
        blocos = [texto[i:i+1000] for i in range(0, len(texto), 1000)]

        embeddings = modelo_embeddings.encode(blocos).tolist()
        ids = [f"{nome_arquivo}_{i}" for i in range(len(blocos))]

        colecao.add(
            ids=ids,
            documents=blocos,
            metadatas=[{"arquivo": nome_arquivo}] * len(blocos),
            embeddings=embeddings
        )
        print(f"✅ {nome_arquivo} indexado ({len(blocos)} blocos)")
    print("🧠 Base de conhecimento pronta!")

def buscar_contexto(pergunta, top_k=3):
    """Busca os trechos mais relevantes no ChromaDB."""
    embedding_pergunta = modelo_embeddings.encode([pergunta]).tolist()[0]
    resultados = colecao.query(query_embeddings=[embedding_pergunta], n_results=top_k)
    textos = resultados["documents"][0]
    metadados = resultados["metadatas"][0]

    contexto = ""
    for t, m in zip(textos, metadados):
        contexto += f"PDF: {m['arquivo']}\nTrecho: {t}\n\n"

    return contexto.strip() if contexto else "Nenhuma informação relevante encontrada."

def gerar_resposta_groq(pergunta, contexto):
    """Envia prompt contextualizado para o modelo Groq."""
    prompt = (
        f"O usuário perguntou:\n{pergunta}\n\n"
        f"Abaixo estão trechos dos manuais e documentos técnicos:\n{contexto}\n\n"
        "Com base nesses documentos, responda da forma mais útil e técnica possível, lembre-se de ser breve e direto "
        "citando o nome do PDF quando relevante."
    )

    resposta = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 1024
        }
    )

    try:
        data = resposta.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("Erro ao obter resposta da Groq:", e)
        return "⚠️ Erro ao gerar resposta."

# ===Flask===

@app.route("/mensagem", methods=["POST"])
def receber_mensagem():
    dados = request.get_json()
    usuario = dados.get("usuario", "Desconhecido")
    pergunta = dados.get("mensagem", "")

    contexto = buscar_contexto(pergunta)
    resposta = gerar_resposta_groq(pergunta, contexto)

    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO conversas (usuario, pergunta, resposta) VALUES (%s, %s, %s)",
            (usuario, pergunta, resposta)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao salvar conversa: {e}")

    return jsonify({"resposta": resposta})

@app.route("/conversas")
def exibir_conversas():
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT usuario, pergunta, resposta, timestamp FROM conversas ORDER BY timestamp DESC")
        registros = cur.fetchall()
        cur.close()
        conn.close()

        html = "<h1>📜 Histórico de Conversas</h1><ul style='font-family: monospace'>"
        for usuario, pergunta, resposta, ts in registros:
            html += f"<li><b>{usuario}</b> [{ts}]<br>🗨️ {pergunta}<br>🤖 {resposta}<br><br></li>"
        html += "</ul>"
        return html
    except Exception as e:
        return f"Erro ao consultar conversas: {e}", 500

@app.route("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    inicializar_banco()

    # Carrega os PDFs se o índice estiver vazio
    if colecao.count() == 0:
        carregar_pdfs_para_chroma("pdfs")
    else:
        print("🧩 Base já existente no ChromaDB — pulando indexação.")

    app.run(host="0.0.0.0", port=5000, debug=True)
