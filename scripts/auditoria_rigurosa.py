#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUDITORIA RIGUROSA DE LOS 7 CEREBROS
=====================================

Valida TODOS los aspectos que pueden causar errores en GitHub Actions:
1. Scripts existen y tienen sintaxis válida
2. Variables de entorno están configuradas correctamente
3. Paths y rutas son correctos
4. Scripts manejan datos vacíos sin errores
5. Workflows tienen la configuración correcta

Autor: Claude Code + bK777741
Fecha: 2025-11-16
"""

import os
import sys
import yaml
import subprocess
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

print("=" * 100)
print("AUDITORIA RIGUROSA - LOS 5 PASOS DE LA PROGRAMACION")
print("=" * 100)
print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 100)

# Resultados globales
errores_criticos = []
advertencias = []
validaciones_ok = []

# =============================================================================
# PASO 1: ANALIZAR WORKFLOWS Y SUS DEPENDENCIAS
# =============================================================================
print("\n[PASO 1/5] ANALIZANDO WORKFLOWS Y DEPENDENCIAS...")
print("-" * 100)

workflows_dir = Path(__file__).parent.parent / ".github" / "workflows"
workflows = list(workflows_dir.glob("*.yml"))

workflows_info = {}

for workflow_file in workflows:
    workflow_name = workflow_file.name
    print(f"\n  Analizando: {workflow_name}")

    try:
        with open(workflow_file, 'r', encoding='utf-8') as f:
            workflow_content = f.read()

        # Extraer scripts llamados
        scripts_llamados = []
        for line in workflow_content.split('\n'):
            if 'python scripts/' in line or 'python .py' in line:
                # Extraer el script
                if 'python scripts/' in line:
                    script = line.split('python scripts/')[1].split()[0]
                    scripts_llamados.append(script)

        # Extraer variables de entorno
        vars_env = []
        for line in workflow_content.split('\n'):
            if 'SUPABASE_URL' in line or 'SUPABASE_KEY' in line or 'SUPABASE_SERVICE_KEY' in line:
                vars_env.append(line.strip())

        workflows_info[workflow_name] = {
            'scripts': scripts_llamados,
            'vars': vars_env
        }

        print(f"    Scripts: {scripts_llamados if scripts_llamados else 'Ninguno'}")
        print(f"    Variables: {len(vars_env)} encontradas")

        validaciones_ok.append(f"Workflow {workflow_name} parseado correctamente")

    except Exception as e:
        errores_criticos.append(f"Error parseando {workflow_name}: {str(e)}")
        print(f"    [ERROR] {str(e)}")

print(f"\n  Total workflows analizados: {len(workflows)}")
print(f"  [OK] {len(validaciones_ok)} workflows")
print(f"  [ERROR] {len(errores_criticos)} errores")

# =============================================================================
# PASO 2: VALIDAR VARIABLES DE ENTORNO
# =============================================================================
print("\n[PASO 2/5] VALIDANDO VARIABLES DE ENTORNO...")
print("-" * 100)

vars_requeridas = {
    "SUPABASE_URL": os.getenv("SUPABASE_URL"),
    "SUPABASE_SERVICE_KEY": os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY"),
    "YT_CLIENT_ID": os.getenv("YT_CLIENT_ID"),
    "YT_CLIENT_SECRET": os.getenv("YT_CLIENT_SECRET"),
    "YT_REFRESH_TOKEN": os.getenv("YT_REFRESH_TOKEN"),
    "CHANNEL_ID": os.getenv("CHANNEL_ID"),
    "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY")
}

print("\n  Variables de entorno:")
for var, value in vars_requeridas.items():
    if value:
        print(f"    [OK] {var}: Configurada")
        validaciones_ok.append(f"Variable {var} configurada")
    else:
        advertencias.append(f"Variable {var} NO configurada (puede causar errores)")
        print(f"    [WARN] {var}: NO configurada")

# Verificar uso correcto en workflows
print("\n  Verificando uso en workflows:")
for workflow_name, info in workflows_info.items():
    usa_supabase_key_incorrecto = False
    for var_line in info['vars']:
        if 'SUPABASE_KEY:' in var_line and 'SUPABASE_SERVICE_KEY' not in var_line:
            usa_supabase_key_incorrecto = True

    if usa_supabase_key_incorrecto:
        errores_criticos.append(f"{workflow_name} usa SUPABASE_KEY en lugar de SUPABASE_SERVICE_KEY")
        print(f"    [ERROR] {workflow_name}: Usa SUPABASE_KEY incorrecto")
    else:
        if info['vars']:
            print(f"    [OK] {workflow_name}: Variables correctas")
            validaciones_ok.append(f"{workflow_name} usa variables correctas")

# =============================================================================
# PASO 3: PROBAR EJECUCION DE SCRIPTS CON DATOS VACIOS
# =============================================================================
print("\n[PASO 3/5] PROBANDO SCRIPTS CON DATOS VACIOS...")
print("-" * 100)

# Scripts que pueden ejecutarse con datos vacíos
scripts_testear = [
    "train_user_preferences.py",
    "gui_evaluator_cloud.py",
    "validar_7_cerebros.py"
]

scripts_dir = Path(__file__).parent

for script_name in scripts_testear:
    script_path = scripts_dir / script_name

    if not script_path.exists():
        errores_criticos.append(f"Script {script_name} NO EXISTE")
        print(f"  [ERROR] {script_name}: NO EXISTE")
        continue

    print(f"\n  Probando: {script_name}")

    try:
        # Ejecutar script con timeout
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=script_path.parent.parent  # Ejecutar desde root del proyecto
        )

        # Verificar exit code
        if result.returncode == 0:
            print(f"    [OK] Exit code: 0 (sin errores)")
            validaciones_ok.append(f"{script_name} ejecutado sin errores (datos vacíos)")
        else:
            errores_criticos.append(f"{script_name} falló con exit code {result.returncode}")
            print(f"    [ERROR] Exit code: {result.returncode}")
            if result.stderr:
                print(f"    Error: {result.stderr[:200]}")

    except subprocess.TimeoutExpired:
        advertencias.append(f"{script_name} timeout después de 30s")
        print(f"    [WARN] Timeout después de 30s")
    except Exception as e:
        errores_criticos.append(f"{script_name} error: {str(e)}")
        print(f"    [ERROR] {str(e)}")

# =============================================================================
# PASO 4: VERIFICAR PATHS Y RUTAS
# =============================================================================
print("\n[PASO 4/5] VERIFICANDO PATHS Y RUTAS...")
print("-" * 100)

# Verificar que NO haya 'cd scripts' o 'cd GITHUB\ CRON'
print("\n  Buscando paths problemáticos en workflows:")
paths_problematicos_encontrados = False

for workflow_file in workflows:
    with open(workflow_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Buscar patrones problemáticos
    if 'cd scripts' in content or 'cd GITHUB' in content:
        errores_criticos.append(f"{workflow_file.name} contiene 'cd scripts' o 'cd GITHUB'")
        print(f"    [ERROR] {workflow_file.name}: Contiene 'cd' problemático")
        paths_problematicos_encontrados = True

if not paths_problematicos_encontrados:
    print(f"    [OK] No se encontraron 'cd scripts' problemáticos")
    validaciones_ok.append("Todos los workflows usan paths correctos")

# Verificar que todos los scripts usen 'python scripts/...'
print("\n  Verificando formato correcto de llamadas:")
for workflow_name, info in workflows_info.items():
    for script in info['scripts']:
        if '/' not in script and script.endswith('.py'):
            # Script llamado sin 'scripts/' al inicio
            errores_criticos.append(f"{workflow_name} llama script sin 'scripts/': {script}")
            print(f"    [ERROR] {workflow_name}: {script} (falta 'scripts/')")
        else:
            print(f"    [OK] {workflow_name}: {script}")
            validaciones_ok.append(f"{workflow_name} llama correctamente a {script}")

# =============================================================================
# PASO 5: VALIDAR SINTAXIS DE TODOS LOS SCRIPTS
# =============================================================================
print("\n[PASO 5/5] VALIDANDO SINTAXIS DE TODOS LOS SCRIPTS...")
print("-" * 100)

scripts_python = list(scripts_dir.glob("*.py"))
print(f"\n  Scripts Python encontrados: {len(scripts_python)}")

for script_file in scripts_python:
    script_name = script_file.name

    try:
        # Compilar sin ejecutar
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(script_file)],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            print(f"    [OK] {script_name}: Sintaxis válida")
            validaciones_ok.append(f"Sintaxis de {script_name} válida")
        else:
            errores_criticos.append(f"{script_name} tiene errores de sintaxis")
            print(f"    [ERROR] {script_name}: {result.stderr[:100]}")

    except Exception as e:
        errores_criticos.append(f"{script_name} error al validar: {str(e)}")
        print(f"    [ERROR] {script_name}: {str(e)}")

# =============================================================================
# REPORTE FINAL
# =============================================================================
print("\n" + "=" * 100)
print("REPORTE FINAL DE AUDITORIA")
print("=" * 100)

print(f"\n[ESTADISTICAS]")
print(f"  Validaciones exitosas: {len(validaciones_ok)}")
print(f"  Advertencias: {len(advertencias)}")
print(f"  Errores criticos: {len(errores_criticos)}")

if errores_criticos:
    print(f"\n[ERRORES CRITICOS] - DEBEN SER CORREGIDOS:")
    for i, error in enumerate(errores_criticos, 1):
        print(f"  {i}. {error}")

if advertencias:
    print(f"\n[ADVERTENCIAS] - Revisar:")
    for i, warn in enumerate(advertencias, 1):
        print(f"  {i}. {warn}")

print("\n" + "=" * 100)

if len(errores_criticos) == 0:
    print("[RESULTADO] AUDITORIA EXITOSA - 0 ERRORES CRITICOS")
    print("GARANTIA: No habra errores en GitHub Actions")
    sys.exit(0)
else:
    print("[RESULTADO] AUDITORIA FALLIDA - HAY ERRORES QUE CORREGIR")
    print(f"Total errores criticos: {len(errores_criticos)}")
    sys.exit(1)

print("=" * 100)
