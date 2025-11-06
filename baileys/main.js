import {
  makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion
} from "@whiskeysockets/baileys";
import { Boom } from "@hapi/boom";
import P from "pino";
import qrcode from "qrcode-terminal";


const fetch = (...args) =>
  import("node-fetch").then(({ default: fetch }) => fetch(...args));

async function startBot() {
  const { state, saveCreds } = await useMultiFileAuthState("./auth");
  const { version } = await fetchLatestBaileysVersion();

  const sock = makeWASocket({
    version,
    logger: P({ level: "silent" }),
    printQRInTerminal: false,
    auth: state,
    browser: ["Bot Baileys", "Chrome", "1.0.0"]
  });

  // ==============================
  //    CONEXÃO E QR CODE
  // ==============================
  sock.ev.on("connection.update", (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      console.clear();
      console.log("📱 Escaneie o QR abaixo:");
      qrcode.generate(qr, { small: true });
    }

    if (connection === "close") {
      const reason = new Boom(lastDisconnect?.error)?.output?.statusCode;
      const shouldReconnect = reason !== DisconnectReason.loggedOut;
      console.log("⚠️ Conexão encerrada:", reason, "→ Reconnect:", shouldReconnect);
      if (shouldReconnect) startBot();
    } else if (connection === "open") {
      console.log("✅ Bot conectado com sucesso!");
    }
  });

  sock.ev.on("creds.update", saveCreds);

  // ==============================
  //   MENSAGENS RECEBIDAS
  // ==============================
  sock.ev.on("messages.upsert", async (msg) => {
    if (msg.type !== "notify") return; // teste ignorar duplicatas
    const m = msg.messages[0];
    if (!m.message || m.key.fromMe) return;

    const sender = m.key.remoteJid;
    const text =
      m.message.conversation ||
      m.message.extendedTextMessage?.text ||
      "";

    //console.log("======================================");
    //console.log(` Nova mensagem recebida de: ${sender}`);
    //console.log(` Conteúdo: ${text}`);
    //console.log("======================================");

    // TESTE: responde imediatamente (para ver se o envio funciona)
    //try {
    //  await sock.sendMessage(sender, { text: "✅ Mensagem recebida! Processando..." });
    //  console.log("📤 Mensagem de confirmação enviada.");
    //} catch (err) {
    //  console.error("❌ Erro ao enviar mensagem de confirmação:", err);
    //}

    // ==============================
    //   COMUNICAÇÃO COM O FLASK
    // ==============================
    try {
      const resposta = await fetch("http://127.0.0.1:5000/mensagem", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ usuario: sender, mensagem: text })
      });

      console.log("Status da API Flask:", resposta.status);

      const texto = await resposta.text();
      console.log("Corpo retornado pelo Flask:", texto);

      let data;
      try {
        data = JSON.parse(texto);
      } catch {
        throw new Error("O Flask não retornou JSON válido!");
      }

      if (!data.resposta) {
        throw new Error("O campo 'resposta' não veio no JSON do Flask!");
      }

      // ==============================
      //    ENVIO DA RESPOSTA
      // ==============================
      await sock.sendMessage(sender, { text: data.resposta });
      console.log(`🤖 Resposta enviada ao usuário: ${data.resposta}`);
    } catch (err) {
      console.error("❌ Erro ao comunicar com Flask ou enviar resposta:", err);
      try {
        await sock.sendMessage(sender, {
          text: "⚠️ Erro ao processar sua mensagem, tente novamente."
        });
      } catch (sendErr) {
        console.error("❌ Falha ao enviar mensagem de erro:", sendErr);
      }
    }
  });
}

startBot();
