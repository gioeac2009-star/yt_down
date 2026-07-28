#!/usr/bin/env python3
import streamlit as st
import os
import ssl
import shutil
import time
import tempfile
try:
    import certifi
    os.environ.setdefault('SSL_CERT_FILE', certifi.where())
    _ctx = ssl.create_default_context(cafile=certifi.where())
    ssl._create_default_https_context = lambda *args, **kwargs: _ctx
except Exception:
    pass

from yt_dlp import YoutubeDL

# Configurações padrão para contornar bloqueios do YouTube (HTTP 403 e verificação de Bot) em IPs da Nuvem
COMMON_YDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'geo_bypass': True,
    'nocheckcertificate': True,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
}

# Clientes do player do YouTube ordenados estrategicamente (iOS e Android contornam bot-check de áudio)
CLIENT_FALLBACKS = [
    ['ios', 'android'],
    ['android', 'ios'],
    ['mweb', 'android'],
    ['tv_embedded'],
    ['web']
]


def human_size(bytes_num):
    if bytes_num is None:
        return "Tamanho desconhecido"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_num < 1024.0:
            return f"{bytes_num:3.1f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.1f} PB"


def format_duration(seconds):
    if not seconds:
        return ""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def list_formats(info):
    formats = info.get('formats', [])
    entries = []
    for f in formats:
        fmt_id = f.get('format_id')
        ext = f.get('ext')
        vcodec = f.get('vcodec')
        acodec = f.get('acodec')
        height = f.get('height') or 0
        fps = f.get('fps') or 0
        abr = f.get('abr') or 0
        filesize = f.get('filesize') or f.get('filesize_approx')
        
        if vcodec != 'none':
            if height:
                quality_label = f"{height}p"
                if height >= 1080:
                    quality_label += " Full HD"
                elif height >= 720:
                    quality_label += " HD"
            else:
                quality_label = f"{f.get('format_note') or 'Vídeo'}"
            if fps and fps > 30:
                quality_label += f" ({int(fps)}fps)"
        else:
            quality_label = f"Áudio {int(abr)} kbps" if abr else "Áudio"
            
        entries.append({
            'id': fmt_id,
            'ext': ext,
            'vcodec': vcodec,
            'acodec': acodec,
            'height': height,
            'fps': fps,
            'abr': abr,
            'size': filesize,
            'label': quality_label,
        })
        
    entries.sort(key=lambda e: (0 if e['vcodec'] != 'none' else 1, -(e['height'] or 0), -(e['abr'] or 0)))
    
    rows = []
    seen = set()
    for e in entries:
        size_str = human_size(e['size'])
        codec = []
        if e['vcodec'] and e['vcodec'] != 'none':
            codec.append(f"{e['vcodec'].split('.')[0]}")
        if e['acodec'] and e['acodec'] != 'none':
            codec.append(f"{e['acodec'].split('.')[0]}")
        codec_str = ' / '.join(codec) if codec else ''
        
        combo_key = (e['label'], e['ext'], size_str)
        if combo_key in seen:
            continue
        seen.add(combo_key)
        
        rows.append({
            'format_id': e['id'],
            'label': e['label'],
            'ext': e['ext'].upper(),
            'codecs': codec_str,
            'size': size_str,
            'display': f"🎬 {e['label']} • {e['ext'].upper()} • {size_str}"
        })
    return rows


# Configuração da página Streamlit
st.set_page_config(
    page_title="YT Downloader — Minimalist",
    page_icon="⚡",
    layout="centered"
)

# Estilização Apple Minimalist
st.markdown("""
<style>
@import url('https://fonts.cdnfonts.com/css/sf-pro-display-cdn');

:root {
    --apple-bg: #F5F5F7;
    --apple-card-bg: #FFFFFF;
    --apple-text-primary: #1D1D1F;
    --apple-text-secondary: #86868B;
    --apple-blue: #0071E3;
    --apple-blue-hover: #0077ED;
    --apple-blue-active: #005BB5;
    --apple-border: rgba(0, 0, 0, 0.08);
    --apple-radius: 18px;
}

/* Fundo da aplicação */
.stApp {
    background-color: var(--apple-bg) !important;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
}

/* Ocultar cabeçalho padrão */
header[data-testid="stHeader"] {
    background: transparent !important;
}

/* Estilo do título principal */
.app-header {
    text-align: center;
    padding: 24px 0 16px 0;
}
.app-title {
    font-size: 2.2rem;
    font-weight: 700;
    color: var(--apple-text-primary);
    letter-spacing: -0.025em;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
}
.app-subtitle {
    font-size: 1.05rem;
    color: var(--apple-text-secondary);
    font-weight: 400;
}

/* Estilizar os containers principais como Cartões Apple */
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlockBorderWrapper"] {
    background-color: var(--apple-card-bg) !important;
    border-radius: var(--apple-radius) !important;
    border: 1px solid var(--apple-border) !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03) !important;
    padding: 24px !important;
    margin-bottom: 20px !important;
}

/* Garantir que colunas internas não dupliquem bordas */
[data-testid="stColumn"] [data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stColumn"] {
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}

/* Rótulos dos inputs */
div[data-testid="stMarkdownContainer"] p, label, .stWidgetLabel p {
    color: var(--apple-text-primary) !important;
    font-weight: 500 !important;
    font-size: 0.95rem !important;
}

/* Inputs de texto */
div[data-baseweb="input"] {
    border-radius: 12px !important;
    border: 1px solid rgba(0, 0, 0, 0.12) !important;
    background-color: #F5F5F7 !important;
    transition: all 0.2s ease-in-out !important;
}
div[data-baseweb="input"]:focus-within {
    border-color: var(--apple-blue) !important;
    box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.18) !important;
    background-color: #FFFFFF !important;
}
div[data-baseweb="input"] input {
    color: var(--apple-text-primary) !important;
    font-size: 0.95rem !important;
}

/* Dropdown / Selectbox */
div[data-baseweb="select"] > div {
    border-radius: 12px !important;
    background-color: #F5F5F7 !important;
    border: 1px solid rgba(0, 0, 0, 0.12) !important;
    color: var(--apple-text-primary) !important;
}

/* Radio buttons */
div[role="radiogroup"] {
    gap: 16px;
}

/* BOTÕES ESTILIZADOS COM TEXTO BRANCO GARANTIDO */
div[data-testid="stButton"] > button,
button[data-baseweb="button"],
.stButton > button {
    background-color: var(--apple-blue) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 12px !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    padding: 10px 20px !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 8px rgba(0, 113, 227, 0.25) !important;
    width: 100% !important;
}
div[data-testid="stButton"] > button:hover,
.stButton > button:hover {
    background-color: var(--apple-blue-hover) !important;
    box-shadow: 0 4px 12px rgba(0, 113, 227, 0.35) !important;
    transform: translateY(-1px);
}
div[data-testid="stButton"] > button:active,
.stButton > button:active {
    background-color: var(--apple-blue-active) !important;
    transform: translateY(0);
}

div[data-testid="stButton"] > button *,
button[data-baseweb="button"] *,
.stButton > button *,
.stButton > button p,
.stButton > button span {
    color: #FFFFFF !important;
    fill: #FFFFFF !important;
}

/* Video metadata styling */
.video-preview-title {
    font-size: 1.15rem;
    font-weight: 600;
    color: var(--apple-text-primary);
    margin-bottom: 8px;
    line-height: 1.35;
}
.video-meta-badge {
    display: inline-flex;
    align-items: center;
    background-color: #F5F5F7;
    color: var(--apple-text-secondary);
    font-size: 0.82rem;
    font-weight: 500;
    padding: 4px 10px;
    border-radius: 20px;
    margin-right: 8px;
    margin-bottom: 6px;
}
.thumbnail-img {
    border-radius: 12px;
    width: 100%;
    object-fit: cover;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

/* Barra de progresso personalizada */
.stProgress > div > div > div > div {
    background-color: var(--apple-blue) !important;
    border-radius: 10px !important;
}
.stProgress > div > div {
    background-color: #E5E5EA !important;
    border-radius: 10px !important;
    height: 8px !important;
}
</style>
""", unsafe_allow_html=True)

# Cabeçalho Minimalista
st.markdown("""
<div class="app-header">
    <div class="app-title">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="24" height="24" rx="6" fill="#0071E3"/>
            <path d="M10 8L16 12L10 16V8Z" fill="white"/>
        </svg>
        YT Downloader
    </div>
    <div class="app-subtitle">Baixe vídeos e áudios do YouTube com elegância e velocidade</div>
</div>
""", unsafe_allow_html=True)

# Estado da sessão
if 'info' not in st.session_state:
    st.session_state['info'] = None
    st.session_state['formats'] = []
if 'last_url' not in st.session_state:
    st.session_state['last_url'] = ""
if 'file_data' not in st.session_state:
    st.session_state['file_data'] = None

# Cartão de busca URL
with st.container(border=True):
    url = st.text_input('Cole a URL do vídeo', placeholder='https://www.youtube.com/watch?v=...')
    get_btn = st.button('Buscar informações')

# Lógica de extração de informações do vídeo
if get_btn and url:
    if url != st.session_state['last_url']:
        st.session_state['info'] = None
        st.session_state['formats'] = []
        st.session_state['last_url'] = url
        st.session_state['file_data'] = None
        
    with st.spinner('Obtendo detalhes do vídeo...'):
        info = None
        last_error = None
        
        for client_types in CLIENT_FALLBACKS:
            ydl_opts = dict(COMMON_YDL_OPTS)
            ydl_opts['extractor_args'] = {'youtube': {'player_client': client_types}}
            try:
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if info:
                        break
            except Exception as e:
                last_error = e
                continue
                
        if info:
            st.session_state['info'] = info
            st.session_state['formats'] = list_formats(info)
        else:
            st.error(f"Não foi possível carregar as informações do vídeo: {last_error}")

# Exibição das opções de download se o vídeo tiver sido encontrado
if st.session_state['info']:
    info = st.session_state['info']
    formats = st.session_state['formats']
    
    with st.container(border=True):
        col_thumb, col_details = st.columns([1, 1.3])
        
        with col_thumb:
            thumbnail_url = info.get('thumbnail')
            if thumbnail_url:
                st.markdown(f'<img src="{thumbnail_url}" class="thumbnail-img"/>', unsafe_allow_html=True)
                
        with col_details:
            st.markdown(f'<div class="video-preview-title">{info.get("title", "Sem título")}</div>', unsafe_allow_html=True)
            
            uploader = info.get('uploader') or info.get('channel')
            duration = format_duration(info.get('duration'))
            view_count = info.get('view_count')
            
            meta_html = ""
            if uploader:
                meta_html += f'<span class="video-meta-badge">👤 {uploader}</span>'
            if duration:
                meta_html += f'<span class="video-meta-badge">⏱️ {duration}</span>'
            if view_count:
                meta_html += f'<span class="video-meta-badge">👁️ {view_count:,} visualizações</span>'
                
            st.markdown(meta_html, unsafe_allow_html=True)

        st.markdown("<hr style='border: none; border-top: 1px solid rgba(0,0,0,0.06); margin: 20px 0;'>", unsafe_allow_html=True)

        if formats:
            options = [r['display'] for r in formats]
            idx_selected = st.selectbox('Selecione a qualidade do vídeo', options, index=0)
            chosen = formats[options.index(idx_selected)]

            download_type = st.radio(
                'Formato final para salvar',
                ['Vídeo completo', 'Apenas Áudio (WAV)'],
                index=0,
                horizontal=True
            )

            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            
            ffmpeg_installed = bool(shutil.which('ffmpeg'))
            if not ffmpeg_installed:
                st.warning("⚠️ 'ffmpeg' não foi detectado no ambiente servidor. Certifique-se de incluir 'ffmpeg' no arquivo 'packages.txt'.")

            if st.button('Processar Download'):
                st.session_state['file_data'] = None
                fmt_id = chosen['format_id']
                acodec = chosen.get('codecs')
                
                # Para extração de Áudio (WAV): se o stream direto de áudio for bloqueado por anti-bot,
                # o sistema automaticamente tenta baixar o vídeo e extrair o áudio de alta qualidade via FFmpeg!
                if download_type == 'Apenas Áudio (WAV)':
                    format_candidates = ['bestaudio/best', fmt_id, 'best']
                    merge_format = 'wav'
                    post_processors = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'wav',
                        'preferredquality': '192',
                    }]
                    mime_type = "audio/wav"
                else:
                    if 'a:' not in (acodec or '') and ('+' not in fmt_id):
                        format_candidates = [f"{fmt_id}+bestaudio/best", fmt_id, 'best']
                    else:
                        format_candidates = [fmt_id, 'best']
                    merge_format = 'mp4'
                    post_processors = []
                    mime_type = "video/mp4"

                progress_bar = st.progress(0)
                status_text = st.empty()

                def make_hook():
                    def hook(d):
                        status_key = d.get('status')
                        if status_key == 'downloading':
                            downloaded = d.get('downloaded_bytes') or 0
                            total = d.get('total_bytes') or d.get('total_bytes_estimate') or None
                            speed = d.get('speed') or 0
                            eta = d.get('eta')
                            percent = int(downloaded / total * 100) if total else 0
                            progress_bar.progress(min(max(percent, 0), 100))
                            
                            eta_str = f" • ETA {eta}s" if eta is not None else ""
                            status_text.caption(
                                f"⚡ Baixando: {human_size(downloaded)} / {human_size(total)} ({percent}%) • {human_size(speed)}/s{eta_str}"
                            )
                        elif status_key == 'finished':
                            progress_bar.progress(100)
                            status_text.caption('✨ Processamento concluído! Preparando arquivo...')
                        elif status_key == 'error':
                            status_text.error('Erro durante o download.')
                    return hook

                download_success = False
                last_error_msg = None

                with tempfile.TemporaryDirectory() as temp_dir:
                    out_template = os.path.join(temp_dir, "%(title)s.%(ext)s")
                    
                    # Estratégia de Fallback Dupla: (1) Formatos -> (2) Clientes de Player (iOS/Android/mweb/tv)
                    for fmt_opt in format_candidates:
                        if download_success:
                            break
                        for client_types in CLIENT_FALLBACKS:
                            ydl_opts = {
                                'format': fmt_opt,
                                'outtmpl': out_template,
                                'progress_hooks': [make_hook()],
                                'noplaylist': True,
                                'prefer_ffmpeg': True,
                                'merge_output_format': merge_format,
                                'postprocessors': post_processors,
                                'quiet': True,
                                'no_warnings': True,
                                'geo_bypass': True,
                                'nocheckcertificate': True,
                                'extractor_args': {
                                    'youtube': {
                                        'player_client': client_types
                                    }
                                },
                                'http_headers': COMMON_YDL_OPTS['http_headers']
                            }

                            try:
                                with YoutubeDL(ydl_opts) as ydl:
                                    ydl.download([url])
                                download_success = True
                                break
                            except Exception as e:
                                last_error_msg = str(e)
                                # Se for bloqueio anti-bot ou 403, avança para a próxima combinação
                                if any(k in last_error_msg for k in ['403', 'Forbidden', 'bot', 'Sign in', 'confirm', 'PO Token']):
                                    continue
                                else:
                                    break

                    if download_success:
                        downloaded_files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir)]
                        if downloaded_files:
                            target_file = downloaded_files[0]
                            file_name = os.path.basename(target_file)
                            with open(target_file, "rb") as f:
                                bytes_content = f.read()

                            st.session_state['file_data'] = {
                                'name': file_name,
                                'bytes': bytes_content,
                                'mime': mime_type
                            }
                            status_text.empty()
                            progress_bar.empty()
                    else:
                        status_text.empty()
                        progress_bar.empty()
                        st.error(f'Erro durante o processamento (Servidor YouTube): {last_error_msg}')

            # Botão de salvar no dispositivo (Web Client-Side Download)
            if st.session_state.get('file_data'):
                fdata = st.session_state['file_data']
                st.success("✅ Arquivo pronto para download!")
                st.download_button(
                    label=f"📥 Clique aqui para salvar \"{fdata['name']}\"",
                    data=fdata['bytes'],
                    file_name=fdata['name'],
                    mime=fdata['mime'],
                    use_container_width=True
                )

        else:
            st.info('Nenhum formato de vídeo disponível foi encontrado para esta URL.')
