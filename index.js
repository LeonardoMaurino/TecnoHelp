const { Client, LocalAuth } = require("whatsapp-web.js");
const qrcode = require("qrcode-terminal");
const fetch = (...args) =>
    import("node-fetch").then(({ default: fetch }) => fetch(...args));

const client = new Client({
    authStrategy: new LocalAuth({ clientId: "bot-principal" }), // sessão separada
    puppeteer: {
        headless: true,
        args: [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--no-first-run",
            "--no-zygote",
            "--disable-gpu",
            "--single-process", // ajuda no Windows
        ],
    },
});

// QR code no terminal
client.on("qr", (qr) => {
    qrcode.generate(qr, { small: true });
});

// Quando conecta
client.once("ready", () => {
    console.log("✅ Bot do WhatsApp conectado!");
});

// Mensagens recebidas
client.on("message", async (msg) => {
    const chat = await msg.getChat();
    const usuario = chat.name || msg.from;
    const pergunta = msg.body;

    console.log(`📩 Mensagem recebida de ${usuario}: ${pergunta}`);

    try {
        // Chama sua API Flask
        const resposta = await fetch("http://127.0.0.1:5000/mensagem", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ usuario, mensagem: pergunta }),
        });

        const data = await resposta.json();

        // Responde no WhatsApp
        msg.reply(data.resposta);
        console.log(`🤖 Resposta enviada: ${data.resposta}`);
    } catch (err) {
        console.error("❌ Erro ao comunicar com Flask:", err);
        msg.reply("⚠️ Erro ao processar sua mensagem, tente novamente.");
    }
});

client.initialize();

