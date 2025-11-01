import os
import subprocess
import shutil
import re
import uuid  # Usado para criar nomes de arquivo únicos
import locale
import sys
from flask import Flask, render_template, request, jsonify

# --- (Configuração do App Flask) ---
app = Flask(__name__)

# Define os caminhos das pastas (baseado na nossa estrutura)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')
VIDEOS_FOLDER = os.path.join(STATIC_FOLDER, 'videos')
# Garante que a pasta de vídeos exista
os.makedirs(VIDEOS_FOLDER, exist_ok=True)


# --- (Lógica copiada e adaptada do seu AniManim.py) ---

def get_scene_name(code):
    """ Tenta encontrar o nome da cena no código. """
    match = re.search(r"class\s+([a-zA-Z0-9_]+)\s*\(\s*([a-zA-Z0-9_.]*Scene)\s*\)\s*:", code)
    if match:
        return match.group(1)
    match = re.search(r"class\s+([a-zA-Z0-9_]+)\s*\(", code)
    if match:
        return match.group(1)
    return None

def get_output_path(base_folder, scene_name, quality_flag):
    """ Calcula o caminho de saída do Manim. """
    quality_folder_map = {"-ql": "480p15", "-qm": "720p30", "-qh": "1080p60", "-qk": "2160p60"}
    folder_name = quality_folder_map.get(quality_flag, "480p15") # Padrão -ql
    
    # CORREÇÃO: Manim usa o nome do arquivo SEM a extensão .py
    folder_sem_extensao = base_folder.replace(".py", "")
    
    return os.path.join("media", "videos", folder_sem_extensao, folder_name, f"{scene_name}.mp4")

def run_manim(code, scene_name, quality_flag):
    """
    Função principal que executa o Manim.
    Baseado na sua lógica _run_manim de AniManim.py
    """
    
    unique_id = str(uuid.uuid4().hex[:8])
    temp_script_name = f"temp_animation_{unique_id}.py"
    
    try:
        with open(temp_script_name, "w", encoding="utf-8") as f:
            f.write(code)

        # CORREÇÃO: Usando "python3 -m manim"
        command = ["python3", "-m", "manim", "--disable_caching", quality_flag, temp_script_name, scene_name]

        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # CORREÇÃO: Definindo o PYTHONPATH
        my_env = os.environ.copy()
        user_site_packages = "/home/aaa/.local/lib/python3.10/site-packages"
        
        existing_path = my_env.get("PYTHONPATH", "")
        if user_site_packages not in existing_path:
             my_env["PYTHONPATH"] = user_site_packages + ":" + existing_path

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     shell=False, 
                                     startupinfo=startupinfo,
                                     env=my_env) # <-- Adicionamos o ambiente corrigido
        
        stdout_bytes, stderr_bytes = process.communicate()
        return_code = process.returncode

        stdout_encoding = getattr(sys.stdout, 'encoding', None) or locale.getpreferredencoding() or 'utf-8'
        stderr_encoding = getattr(sys.stderr, 'encoding', None) or locale.getpreferredencoding() or 'utf-8'
        
        stdout_str = stdout_bytes.decode(stdout_encoding, errors='replace')
        stderr_str = stderr_bytes.decode(stderr_encoding, errors='replace')

        if return_code != 0:
            error_message = f"MANIM ERRO (Código: {return_code}):\n\n--- Saída de Erro (stderr) ---\n{stderr_str}\n\n--- Saída Padrão (stdout) ---\n{stdout_str}"
            return {"status": "error", "message": error_message.strip()}

        # O script procura o caminho correto agora
        output_file_original = get_output_path(temp_script_name, scene_name, quality_flag)

        if not os.path.exists(output_file_original):
            error_msg = (f"Renderização concluída (Manim OK), mas não encontrou '{output_file_original}'\n\n"
                         f"--- stdout ---\n{stdout_str}\n\n--- stderr ---\n{stderr_str}")
            return {"status": "error", "message": error_msg.strip()}

        final_video_name = f"{scene_name}_{unique_id}.mp4"
        final_video_path_destino = os.path.join(VIDEOS_FOLDER, final_video_name)
        
        shutil.move(output_file_original, final_video_path_destino)

        # --- INÍCIO DA CORREÇÃO ---
        # Definindo a variável 'folder_sem_extensao' que faltava
        folder_sem_extensao = temp_script_name.replace(".py", "")
        # --- FIM DA CORREÇÃO ---
        
        temp_media_dir = os.path.join("media", "videos", folder_sem_extensao) # <-- Agora funciona
        if os.path.exists(temp_media_dir):
            shutil.rmtree(temp_media_dir, ignore_errors=True)

        video_url_web = f"/static/videos/{final_video_name}"
        return {"status": "success", "url": video_url_web, "message": stdout_str}

    except Exception as e:
        import traceback
        tb_str = traceback.format_exc()
        error_msg = f"Erro Inesperado no Servidor:\n{type(e).__name__}: {e}\n\nTraceback:\n{tb_str}"
        return {"status": "error", "message": error_msg}
    finally:
        if os.path.exists(temp_script_name):
            try: os.remove(temp_script_name)
            except Exception: pass


# --- (Rotas do Flask) ---

@app.route('/')
def index():
    """ Rota 1: Serve a página HTML principal. """
    return render_template('index.html')

@app.route('/render', methods=['POST'])
def handle_render():
    """ Rota 2: Recebe o código, executa e retorna o JSON. """
    
    data = request.json
    code = data.get('code', '')
    quality_flag = data.get('quality', '-ql') # Pega a flag de qualidade

    if not code.strip():
        return jsonify({"status": "error", "message": "Erro: O campo de código está vazio."}), 400

    scene_name = get_scene_name(code)
    if not scene_name:
        return jsonify({"status": "error", "message": "Erro: Não foi possível encontrar o nome da Cena (ex: class MinhaCena(Scene):)"}), 400

    result = run_manim(code, scene_name, quality_flag)
    
    return jsonify(result)


# --- (Ponto de entrada para rodar o servidor) ---
if __name__ == '__main__':
    # Usando a porta 5001 e desabilitando o reloader
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
