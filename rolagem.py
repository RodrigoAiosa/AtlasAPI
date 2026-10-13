"""Rola a página até um elemento depois de um clique.

O Streamlit refaz a página e mantém a rolagem onde estava; com 56 botões de
categoria, a lista escolhida fica fora da tela. Este script roda num iframe
de 1px (mesma técnica de esconder_selo.py) e rola a página do app até o
elemento com o id informado.
"""

import streamlit as st

_SCRIPT = """
<script>
// pedido {pedido}
(function() {{
    let tentativas = 0;
    function rolar() {{
        try {{
            const alvo = window.parent.document.getElementById("{alvo}");
            if (alvo) {{ alvo.scrollIntoView({{behavior: "smooth", block: "start"}}); return; }}
        }} catch (e) {{ return; }}
        if (++tentativas < 30) setTimeout(rolar, 100);
    }}
    rolar();
}})();
</script>
"""


def pedir(alvo: str) -> None:
    """Marca que, na próxima execução, a página deve rolar até `alvo`."""
    st.session_state["rolar_ate"] = alvo


def executar(alvo: str) -> None:
    """Rola até `alvo` se isso foi pedido no clique anterior."""
    if st.session_state.get("rolar_ate") != alvo:
        return
    st.session_state.pop("rolar_ate")
    # O número muda a cada pedido para o Streamlit desenhar o iframe de novo e o script rodar outra vez.
    pedido = st.session_state["rolar_pedidos"] = st.session_state.get("rolar_pedidos", 0) + 1
    codigo = _SCRIPT.format(alvo=alvo, pedido=pedido)
    if hasattr(st, "iframe"):
        st.iframe(codigo, height=1)
    else:
        import streamlit.components.v1 as components
        components.html(codigo, height=1)
