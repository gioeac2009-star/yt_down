# Deploy do YT Downloader no Streamlit Cloud

Esta pasta contém todos os arquivos otimizados especificamente para a nuvem (**Streamlit Cloud / GitHub**).

## 📁 Arquivos Incluídos

1. **`packages.txt`**:
   - Contém a instrução `ffmpeg`.
   - **Crucial:** O Streamlit Cloud detecta este arquivo e instala automaticamente o `ffmpeg` no servidor Linux de forma nativa! Isso corrige o erro de fusão de áudio/vídeo.

2. **`requirements.txt`**:
   - As dependências Python necessárias (`streamlit`, `yt-dlp`, `certifi`).

3. **`yt_download_streamlit.py`**:
   - O aplicativo Streamlit adaptado para a Web.
   - Baixa o vídeo temporariamente no servidor e gera um botão de download (`st.download_button`) para transferir o arquivo diretamente para o celular ou computador do usuário.

---

## 🚀 Como Atualizar no GitHub / Streamlit Cloud

### Opção A: Usar esta pasta como raiz do seu repositório GitHub
Se o seu repositório no GitHub contiver os arquivos desta pasta (`packages.txt`, `requirements.txt`, `yt_download_streamlit.py`) na raiz:
1. Faça o `git push` das alterações.
2. O Streamlit Cloud irá recompilar o app automaticamente, instalar o `ffmpeg` e rodar sem erros!

### Opção B: Apontar no Streamlit Cloud
Nas configurações do seu app no **Streamlit Cloud** (`Manage app` -> `Settings`):
- Certifique-se de que o **Main file path** esteja apontando para `deploy_streamlit/yt_download_streamlit.py` (ou mova os arquivos de `deploy_streamlit` para a raiz do repositório se preferir).
