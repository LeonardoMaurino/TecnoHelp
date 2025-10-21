from flask import Flask, request, jsonify, render_template, redirect, url_for
import os
import psycopg2 # Biblioteca para conectar ao banco PostgreSQL
import PyPDF2 # Para leitura de PDFs
import requests  # Para fazer chamadas HTTP (API Groq)

app = Flask(__name__)

DB_CONFIG = {
    'host': 'localhost',
    'dbname': 'postgres',
    'user': 'postgres',
    'password': 'insira sua_senha_aqui',
}

GROQ_API_KEY = "insira_sua_groq_api_key_aqui"
GROQ_MODEL = "llama-3.3-70b-versatile"

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
        print("✨ Tabela 'conversas' verificada/criada com sucesso.")
    except Exception as e:
        print(f"😣 Erro ao criar tabela: {e}")

def extrair_texto_pdf(caminho_pdf):
    try:
        with open(caminho_pdf, 'rb') as f:
            leitor = PyPDF2.PdfReader(f)
            texto = ''
            for pagina in leitor.pages:
                pagina_texto = pagina.extract_text()
                if pagina_texto:
                    texto += pagina_texto + '\n'
            return texto.strip()
    except Exception as e:
        print(f"Erro ao extrair {caminho_pdf}: {e}")
        return ''

def carregar_pdfs_com_texto(pasta='pdfs'):
    documentos = []
    print("📁 Verificando PDF na pasta...", flush=True)
    for nome_arquivo in os.listdir(pasta):
        if nome_arquivo.lower().endswith('.pdf'):
            caminho = os.path.join(pasta, nome_arquivo)
            conteudo = extrair_texto_pdf(caminho)
            print(f"📄 {nome_arquivo} -> {len(conteudo)} caracteres extraídos", flush=True)
            documentos.append({"nome": nome_arquivo, "conteudo": conteudo})
    print(f"🔍 Total de documentos carregados: {len(documentos)}", flush=True)
    return documentos

def escolher_pdfs_com_llm(pergunta, documentos):

    if not GROQ_API_KEY:
        return "Sistema sem acesso à LLM. Não é possível responder agora."

    documentos_limitados = documentos[:2]
    contexto = "\n\n".join([
        f"PDF: {doc['nome']}\nConteúdo: {doc['conteudo'][:10000]}"
        for doc in documentos_limitados
    ])

    prompt = (
        f"O usuário descreveu o seguinte problema técnico:\n"
        f"\"\"\"{pergunta}\"\"\"\n\n"
        f"Abaixo estão trechos de documentos de suporte técnico:\n\n"
        f"{contexto}\n\n"
        "Baseado nisso, responda ao problema do usuário da forma mais precisa possível, "
        "citando o(s) trecho(s) mais relevantes dos documentos. "
        "Inclua o nome do documento antes de cada trecho, assim:\n\n"
        "PDF: nome_do_arquivo.pdf\nTrecho: ...\n\n"
        "Considere no máximo dois documentos relevantes e responda com base apenas neles. "
        "Se não encontrar nenhuma informação útil, diga apenas 'Nenhuma informação relevante encontrada'."
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
            "max_tokens": 1024,
            "top_p": 1,
            "stream": False
        }
    )

    try:
        resultado = resposta.json()
        conteudo = resultado['choices'][0]['message']['content']
        if not conteudo.strip():
            return "⚠️ Nenhuma resposta foi gerada."
        return conteudo.strip()
    except Exception as e:
        print(f"❌ Erro na resposta da LLM: {e}")
        return "⚠️ Erro ao processar a resposta. Tente novamente."

@app.route('/mensagem', methods=['POST'])
def receber_mensagem():
    dados = request.get_json()
    usuario = dados.get('usuario')
    pergunta = dados.get('mensagem')

    documentos = carregar_pdfs_com_texto()
    resposta_final = escolher_pdfs_com_llm(pergunta, documentos)

    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO conversas (usuario, pergunta, resposta) VALUES (%s, %s, %s)",
            (usuario, pergunta, resposta_final)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao salvar conversa: {e}")

    return jsonify({'resposta': resposta_final})

@app.route('/conversas')
def exibir_conversas():
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT usuario, pergunta, resposta, timestamp FROM conversas ORDER BY timestamp DESC")
        registros = cur.fetchall()
        cur.close()
        conn.close()
        html = '<h1>📜 Histórico de Conversas</h1><ul style="font-family: monospace">'
        for usuario, pergunta, resposta, ts in registros:
            html += f'<li><b>{usuario}</b> [{ts}]<br>🗨️ {pergunta}<br>🤖 {resposta}<br><br></li>'
        html += '</ul>'
        return html
    except Exception as e:
        return f"Erro ao consultar conversas: {e}", 500

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/neon')
def tema_neon():
    return render_template('neon.html')


if __name__ == '__main__':
    inicializar_banco()
    app.run(debug=True)
    app.run(host="0.0.0.0", port=5000, debug=True)

# lets all love lain <3