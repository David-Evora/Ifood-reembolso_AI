"use strict";

// Todo texto vindo do servidor entra na página com textContent, nunca como HTML.
const ROTULOS = {
  ELEGIVEL: ["✔", "Elegível a reembolso", "ok"],
  PODE_NAO_ELEGIVEL: ["!", "Pode não ser elegível", "aviso"],
  VALIDACAO_MANUAL: ["!", "Validação manual necessária", "aviso"],
  ANTIFRAUDE: ["⚠", "Encaminhar ao antifraude", "risco"],
  ORIENTACAO: ["i", "Orientação financeira", "info"],
  FALLBACK: ["?", "Sem confiança para decidir", "risco"],
};

const EXEMPLOS = [
  ["Saiu para entrega, sem causa", "O cliente quer reembolso, mas o pedido já saiu para entrega. Ainda é permitido?", ""],
  ["Erro do restaurante", "O pedido já saiu para entrega, mas foi erro do restaurante. O cliente quer reembolso.", ""],
  ["Desistência do cliente", "O pedido já saiu para entrega e o cliente desistiu. Ainda tem reembolso?", ""],
  ["Pedido 1001 (API)", "Cliente quer reembolso, pedido já despachado.", "1001"],
  ["Falta de ingrediente", "O restaurante cancelou por falta de ingrediente. O reembolso é automático?", ""],
  ["Cobrado após cancelar", "O cliente foi cobrado após o cancelamento. O que fazer?", ""],
  ["Não autorizou", "Pedido saiu para entrega, mas o cliente afirma que não autorizou.", ""],
  ["Suspeita de fraude", "Suspeita de fraude no cartão do pedido, cliente quer reembolso.", ""],
];

const $ = (id) => document.getElementById(id);

function el(tag, props = {}, filhos = []) {
  const e = document.createElement(tag);
  Object.assign(e, props);
  for (const f of [].concat(filhos)) e.append(f);
  return e;
}

function lista(titulo, itens, tag = "ul", cls = "") {
  if (!itens || !itens.length) return [];
  return [el("h2", { textContent: titulo }), el(tag, { className: cls }, itens.map((t) => el("li", { textContent: t })))];
}

function mostrar(conteudo) {
  const r = $("resultado");
  r.replaceChildren(...conteudo);
  r.hidden = false;
  r.focus();
}

function mostrarErro(msg) {
  mostrar([el("p", { className: "erro", role: "alert", textContent: msg })]);
}

function mostrarResposta(d) {
  const [icone, rotulo, cls] = ROTULOS[d.decisao] ?? ["?", d.decisao, "info"];
  const partes = [
    el("span", { className: `badge ${cls}` }, [el("span", { ariaHidden: "true", textContent: icone }), rotulo]),
    el("p", { className: "resumo", textContent: d.resumo }),
    el("div", { className: "confianca" }, [
      "Confiança",
      el("meter", { min: 0, max: 1, value: d.confianca, textContent: String(d.confianca) }),
      `${Math.round(d.confianca * 100)}%`,
    ]),
    ...lista("O que fazer", d.passos, "ol"),
    ...lista("Informação que falta", d.faltando),
    ...lista("Por que não decidi", d.motivos_baixa_confianca),
    ...lista("Fontes", d.fontes, "ul", "fontes"),
  ];
  if (d.precisa_humano && /^https?:\/\//.test(d.suporte_url ?? "")) {
    partes.push(el("h2", { textContent: "Suporte" }),
      el("a", { href: d.suporte_url, target: "_blank", rel: "noopener noreferrer", textContent: "Abrir canal de suporte" }));
  }
  partes.push(el("details", {}, [
    el("summary", { textContent: "Detalhes técnicos" }),
    el("pre", { textContent: JSON.stringify({ evidencias: d.evidencias, trace: d.trace }, null, 2) }),
  ]));
  mostrar(partes);
}

async function enviar(ev) {
  ev.preventDefault();
  const pergunta = $("pergunta").value.trim();
  const pedido = $("pedido").value.trim();
  if (pergunta.length < 3) return mostrarErro("Descreva o caso com pelo menos 3 caracteres.");
  if (pedido && !/^\d{3,20}$/.test(pedido)) return mostrarErro("O número do pedido deve ter de 3 a 20 dígitos.");

  $("enviar").disabled = true;
  $("status").textContent = "Consultando…";
  try {
    const r = await fetch("/api/perguntar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pergunta, pedido_id: pedido || null }),
    });
    const dados = await r.json().catch(() => ({}));
    if (dados.decisao) mostrarResposta(dados);
    else if (r.status === 401) mostrarErro("Sessão expirada. Recarregue a página e entre de novo.");
    else if (r.status === 422) mostrarErro("Entrada inválida. Confira a descrição e o número do pedido.");
    else mostrarErro(dados.erro ?? `Erro inesperado (${r.status}).`);
  } catch {
    mostrarErro("Não consegui falar com o servidor.");
  } finally {
    $("enviar").disabled = false;
    $("status").textContent = "";
  }
}

$("form").addEventListener("submit", enviar);
$("exemplos").append(...EXEMPLOS.map(([nome, texto, pedido]) =>
  el("button", {
    type: "button", className: "chip", textContent: nome,
    onclick: () => { $("pergunta").value = texto; $("pedido").value = pedido; $("pergunta").focus(); },
  })));
