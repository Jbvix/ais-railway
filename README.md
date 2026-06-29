# Projeto AIS – Monitoramento da Frota em Suape

Este projeto implementa uma solução de **monitoramento em tempo real** da frota de rebocadores via dados **AIS (Automatic Identification System)**, com foco nos terminais do Porto de Suape.

## 📌 Arquivos principais

- **`ais_suape_kmz_kpi.py`** → Script principal que:
  - Conecta no AISStream.io via WebSocket;
  - Filtra MMSIs da frota configurada;
  - Detecta entrada/saída de embarcações nas geofences;
  - Gera **KPIs** e relatórios automáticos em PDF.

- **`geofences_from_kmz.py`** → Contém os polígonos dos terminais (CMU, PGL-1, PGL-2, PGL-3A, PGL3B) convertidos de arquivos KMZ para listas de coordenadas `[lat, lon]`.

- **`server.py`** → API FastAPI para rodar no **Railway**, que expõe:
  - `/health` – status;
  - `/geofences` – polígonos dos terminais;
  - `/kpis` – indicadores da frota;
  - `/events` – eventos ENTER/EXIT;
  - `/positions` – posições recentes.

- **`index.html`** (dashboard) → Interface web em **Leaflet + Tailwind** para visualizar:
  - KPIs da frota;
  - Posições em tempo real no mapa;
  - Polígonos das geofences;
  - Últimos eventos ENTER/EXIT.

- **`.gitignore`** → Configuração para ignorar arquivos temporários, ambientes virtuais, logs, PDFs e credenciais.

---

## 🚀 Deploy

### Backend (Railway)
1. Crie um repositório com `server.py`, `geofences_from_kmz.py`, `requirements.txt` e `Procfile`.
2. No **Railway**, configure as variáveis de ambiente:
   - `AISSTREAM_API_KEY` → sua chave do AISStream.io;
   - `MMSI_LIST` → lista de MMSIs separados por vírgula.
3. Deploy automático via GitHub.
4. Teste em: `https://<seu-servico>.up.railway.app/kpis`

### Frontend (Netlify)
1. Publique o `index.html` no Netlify.
2. Ajuste os endpoints no HTML para apontar para a API do Railway.
3. Acesse em: `https://<seu-dashboard>.netlify.app`

---

## ⚙️ Instalação local
```bash
# Clonar repositório
git clone https://github.com/seu-usuario/ais-suape.git
cd ais-suape

# Criar venv
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts/activate     # Windows

# Instalar dependências
pip install -r requirements.txt

# Rodar script principal
$env:AISSTREAM_API_KEY="SUA_CHAVE"
python ais_suape_kmz_kpi.py
```

---

## 📊 Roadmap
- [x] Conexão AISStream e filtragem por frota
- [x] Geofences em Suape
- [x] Relatórios PDF automáticos
- [x] Dashboard HTML
- [ ] Deploy backend no Railway
- [ ] Deploy frontend no Netlify
- [ ] CSV exportável para BI
- [ ] Alertas automáticos via Telegram/E-mail
- [ ] Dashboards em Grafana/Power BI

---

## 👨‍✈️ Autor
Desenvolvido por **Charlie Bravo (Jossian Brito)** ⚓

Marinha Mercante · Rebocadores Portuários · Inovação Digital

## Licença e Copyright

**Copyright (c) 2026 Jossian Brito**

Este projeto é licenciado sob a **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**.

- Uso comercial não é permitido sem autorização expressa prévia do autor.
- A atribuição ao autor original é obrigatória.

O texto completo da licença está no arquivo [LICENSE](LICENSE).