# -*- coding: utf-8 -*-
__title__ = "Colorir\nTubos"
__author__ = "AlexJR"
__version__ = "Versão 1.1"
__doc__ = """
_____________________________________________________________________
Descrição:

Coloriza tubos rígidos automaticamente baseado na abreviatura do sistema.
Aplica materiais nas faces dos tubos de forma otimizada.

Lógica de busca de material (cascata):
  1. Tenta "Abreviatura do Sistema - Nome do Tipo" (ex: UnMEP Pluv - Série Reforçada)
  2. Se não encontrar, tenta somente "Abreviatura do Sistema" (ex: UnMEP Pluv)
_____________________________________________________________________
Passo a passo:

1. Certifique-se que cada sistema tem o campo "Abreviatura do sistema" preenchido
2. Crie materiais no Revit com os nomes no formato "Abreviatura - Nome do Tipo"
   ou apenas "Abreviatura" como fallback
3. Execute o script e informe o nome do parâmetro
4. Escolha se deseja limpar colorização existente
5. Aguarde o processamento e veja o relatório

_____________________________________________________________________
Última atualização:
- [09.01.2025] - VERSÃO 1.0
- [06.03.2025] - VERSÃO 1.1 - Busca por material combinando Abreviatura + Nome do Tipo
"""

# ___  __  __  ____    ___   ____   _____  ____
# |_ _||  \/  ||  _ \  / _ \ |  _ \ |_   _|/ ___|
# | | | |\/| || |_) || | | || |_) |  | |  \___ \
# | | | |  | ||  __/ | |_| ||  _ <   | |   ___) |
# |___||_|  |_||_|     \___/ |_| \_\  |_|  |____/
# =================================================

# Importações Python e .NET
import clr
import os

# Importações Revit API
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

# Importações pyRevit
from pyrevit import forms, script

# Variáveis globais do Revit
doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
app = __revit__.Application

# Obtém output do pyRevit
output = script.get_output()


# _____  _   _  _   _   ____  _____  ___   ___   _   _  ____
# |  ___|| | | || \ | | / ___||_   _||_ _| / _ \ | \ | |/ ___|
# | |_   | | | ||  \| || |      | |   | | | | | ||  \| |\___ \
# |  _|  | |_| || |\  || |___   | |   | | | |_| || |\  | ___) |
# |_|     \___/ |_| \_| \____|  |_|  |___| \___/ |_| \_||____/


def get_all_pipes():
    """Coleta todos os tubos rígidos do documento"""
    collector = FilteredElementCollector(doc) \
        .OfCategory(BuiltInCategory.OST_PipeCurves) \
        .WhereElementIsNotElementType()
    return list(collector)


def get_material_by_name(material_name):
    """Busca material pelo nome exato no documento"""
    if not material_name or material_name.strip() == "":
        return None

    collector = FilteredElementCollector(doc).OfClass(Material)

    for mat in collector:
        if mat.Name == material_name:
            return mat
    return None


def get_system_abbreviation(pipe, param_name):
    """Obtém a abreviatura do sistema do tubo"""
    try:
        # Tenta pegar o parâmetro customizado diretamente no tubo
        param = pipe.LookupParameter(param_name)
        if param and param.HasValue:
            value = param.AsString()
            if value:
                return value.strip()

        # Fallback: tenta pegar do MEPSystem
        if hasattr(pipe, 'MEPSystem') and pipe.MEPSystem:
            system = pipe.MEPSystem
            abbrev_param = system.LookupParameter(param_name)
            if abbrev_param and abbrev_param.HasValue:
                value = abbrev_param.AsString()
                if value:
                    return value.strip()

        return None
    except:
        return None


def get_pipe_type_name(pipe):
    """Obtém o Nome do Tipo do tubo.

    O PipeType está no parâmetro "Família e tipo" / "Tipo" / "ID de tipo"
    (todos apontam para ElementId:3163752 no dump).
    O nome do tipo é obtido via ALL_MODEL_TYPE_NAME no elemento apontado.
    """
    try:
        # Pega o ElementId do tipo do tubo via GetTypeId()
        type_id = pipe.GetTypeId()
        if type_id and type_id.IntegerValue > 0:
            el = doc.GetElement(type_id)
            if el is not None:
                # Tenta ALL_MODEL_TYPE_NAME primeiro
                try:
                    name_param = el.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME)
                    if name_param and name_param.HasValue:
                        val = name_param.AsString()
                        if val and val.strip():
                            return val.strip()
                except:
                    pass
                # Tenta SYMBOL_NAME_PARAM
                try:
                    sym_param = el.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
                    if sym_param and sym_param.HasValue:
                        val = sym_param.AsString()
                        if val and val.strip():
                            return val.strip()
                except:
                    pass
                # Tenta .Name diretamente
                try:
                    if el.Name and el.Name.strip():
                        return el.Name.strip()
                except:
                    pass

        # Fallback: busca pelo parâmetro "Família e tipo" / "Tipo" / "ID de tipo"
        target_names = ("família e tipo", "family and type", "tipo", "type", "id de tipo", "type id")
        for param in pipe.Parameters:
            try:
                pname = param.Definition.Name.lower()
                if pname in target_names and param.HasValue:
                    eid = param.AsElementId()
                    if eid and eid.IntegerValue > 0:
                        el = doc.GetElement(eid)
                        if el is not None:
                            try:
                                name_param = el.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME)
                                if name_param and name_param.HasValue:
                                    val = name_param.AsString()
                                    if val and val.strip():
                                        return val.strip()
                            except:
                                pass
                            try:
                                if el.Name and el.Name.strip():
                                    return el.Name.strip()
                            except:
                                pass
            except:
                continue

        return None
    except:
        return None


def debug_pipe_params(pipe):
    """Lista todos os parâmetros do tubo para diagnóstico"""
    lines = []
    for param in pipe.Parameters:
        try:
            pname = param.Definition.Name
            if param.HasValue:
                storage = param.StorageType
                if str(storage) == "String":
                    val = param.AsString()
                elif str(storage) == "ElementId":
                    eid = param.AsElementId()
                    el = doc.GetElement(eid) if eid else None
                    el_name = "?"
                    if el is not None:
                        try:
                            el_name = el.Name
                        except:
                            try:
                                np = el.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME)
                                el_name = np.AsString() if np and np.HasValue else "?(sem ALL_MODEL_TYPE_NAME)"
                            except:
                                el_name = "?(erro)"
                    val = "ElementId:{} ({})".format(eid.IntegerValue if eid else "?", el_name)
                elif str(storage) == "Integer":
                    val = str(param.AsInteger())
                elif str(storage) == "Double":
                    val = str(round(param.AsDouble(), 4))
                else:
                    val = "[{}]".format(storage)
            else:
                val = "(sem valor)"
            lines.append("  - **{}**: {}".format(pname, val))
        except:
            lines.append("  - [erro ao ler param]")
    return lines


def resolve_material(abbreviation, type_name):
    """
    Busca o material em cascata:
      1. "Abreviatura - Nome do Tipo"  (ex: UnMEP Pluv - Série Reforçada)
      2. "Abreviatura"                 (ex: UnMEP Pluv)

    Retorna: (material, nome_usado, usou_fallback)
    """
    # Tentativa 1: combinação Abreviatura + Nome do Tipo
    if type_name:
        combined_name = "{} - {}".format(abbreviation, type_name)
        material = get_material_by_name(combined_name)
        if material:
            return material, combined_name, False

    # Tentativa 2: somente a Abreviatura
    material = get_material_by_name(abbreviation)
    if material:
        return material, abbreviation, True

    return None, None, False


def paint_pipe_faces(pipe, material):
    """Pinta todas as faces do tubo com o material especificado"""
    if not material:
        return 0

    painted_count = 0

    try:
        # Opções de geometria
        options = Options()
        options.ComputeReferences = True
        options.IncludeNonVisibleObjects = False

        geom = pipe.get_Geometry(options)
        if not geom:
            return 0

        # Processa cada elemento geométrico
        for geom_obj in geom:
            if isinstance(geom_obj, Solid):
                # Processa faces do sólido
                for face in geom_obj.Faces:
                    if not doc.IsPainted(pipe.Id, face):
                        doc.Paint(pipe.Id, face, material.Id)
                        painted_count += 1

            elif isinstance(geom_obj, GeometryInstance):
                # Processa instâncias de geometria
                inst_geom = geom_obj.GetInstanceGeometry()
                if inst_geom:
                    for inst_obj in inst_geom:
                        if isinstance(inst_obj, Solid):
                            for face in inst_obj.Faces:
                                if not doc.IsPainted(pipe.Id, face):
                                    doc.Paint(pipe.Id, face, material.Id)
                                    painted_count += 1

        return painted_count
    except Exception as e:
        return 0


def remove_all_paint(pipe):
    """Remove toda a pintura de um tubo"""
    try:
        options = Options()
        options.ComputeReferences = True
        geom = pipe.get_Geometry(options)

        if not geom:
            return

        for geom_obj in geom:
            if isinstance(geom_obj, Solid):
                for face in geom_obj.Faces:
                    if doc.IsPainted(pipe.Id, face):
                        doc.RemovePaint(pipe.Id, face)

            elif isinstance(geom_obj, GeometryInstance):
                inst_geom = geom_obj.GetInstanceGeometry()
                if inst_geom:
                    for inst_obj in inst_geom:
                        if isinstance(inst_obj, Solid):
                            for face in inst_obj.Faces:
                                if doc.IsPainted(pipe.Id, face):
                                    doc.RemovePaint(pipe.Id, face)
    except:
        pass


def main():
    """Função principal"""

    # Interface: pede o nome do parâmetro
    param_name = forms.ask_for_string(
        default="Abreviatura do sistema",
        prompt="Nome do parâmetro de abreviatura do sistema:",
        title="Colorização de Tubos"
    )

    if not param_name:
        forms.alert("Operação cancelada.", exitscript=True)

    # Pergunta se quer limpar materiais antes
    remove_paint_option = forms.alert(
        "Deseja REMOVER toda a colorização existente antes de aplicar as novas cores?",
        yes=True,
        no=True,
        title="Limpar Colorização"
    )

    # Coleta tubos
    output.print_md("## 🔍 Coletando tubos...")
    pipes = get_all_pipes()

    if not pipes:
        forms.alert("Nenhum tubo encontrado no documento!", exitscript=True)

    output.print_md("**Total de tubos:** {}".format(len(pipes)))
    output.print_md("\n> 🔎 Lógica de busca: **Abreviatura + Nome do Tipo** → fallback para **Abreviatura**")

    # Estatísticas
    stats = {
        'total': len(pipes),
        'coloridos': 0,
        'coloridos_combinado': 0,   # pintados com "Abrev - Tipo"
        'coloridos_fallback': 0,    # pintados só com "Abrev"
        'sem_abreviatura': 0,
        'sem_material': 0,
        'erro': 0,
        'faces_pintadas': 0,
        'limpos': 0
    }

    # Materiais faltantes: guarda o nome combinado e o fallback tentado
    materiais_faltantes = set()

    # Inicia transação
    t = Transaction(doc, "Colorir Tubos por Sistema")
    t.Start()

    try:
        # Remove pintura se solicitado
        if remove_paint_option:
            output.print_md("\n## 🧹 Removendo colorização existente...")
            for pipe in pipes:
                remove_all_paint(pipe)
                stats['limpos'] += 1
            output.print_md("**Tubos limpos:** {}".format(stats['limpos']))

        # Processa cada tubo
        output.print_md("\n## 🎨 Aplicando colorização...")

        # Diagnóstico: mostra os primeiros 5 tubos em detalhe
        output.print_md("\n### 🔬 DIAGNÓSTICO (primeiros 5 tubos)")
        output.print_md("| ID | Abreviatura | Nome do Tipo | Nome Combinado | Material Combinado | Material Fallback |")
        output.print_md("|---|---|---|---|---|---|")
        diag_count = 0
        diag_params_done = False

        for i, pipe in enumerate(pipes):
            # Progress
            if (i + 1) % 50 == 0:
                output.print_md("Processando: {}/{}".format(i + 1, len(pipes)))

            try:
                # Obtém abreviatura
                abbrev = get_system_abbreviation(pipe, param_name)

                if not abbrev:
                    stats['sem_abreviatura'] += 1
                    if diag_count < 5:
                        output.print_md("| {} | *(sem abreviatura)* | - | - | - | - |".format(pipe.Id.IntegerValue))
                        diag_count += 1
                    continue

                # Obtém Nome do Tipo
                type_name = get_pipe_type_name(pipe)

                # Diagnóstico: dump completo de params do primeiro tubo se tipo ainda None
                if not diag_params_done and type_name is None:
                    diag_params_done = True
                    output.print_md("\n#### ⚙️ DUMP de parâmetros do tubo ID {} (tipo retornou None)".format(pipe.Id.IntegerValue))
                    for line in debug_pipe_params(pipe):
                        output.print_md(line)

                # Diagnóstico: tabela dos primeiros 5 tubos
                if diag_count < 5:
                    combined_name = "{} - {}".format(abbrev, type_name) if type_name else "*(sem tipo)*"
                    mat_combined = get_material_by_name(combined_name)
                    mat_fallback = get_material_by_name(abbrev)
                    output.print_md("| {} | `{}` | `{}` | `{}` | {} | {} |".format(
                        pipe.Id.IntegerValue,
                        abbrev,
                        type_name if type_name else "*(None)*",
                        combined_name,
                        "✅ **{}**".format(mat_combined.Name) if mat_combined else "❌ não encontrado",
                        "✅ **{}**".format(mat_fallback.Name) if mat_fallback else "❌ não encontrado"
                    ))
                    diag_count += 1

                # Busca material em cascata
                material, nome_usado, usou_fallback = resolve_material(abbrev, type_name)

                if not material:
                    stats['sem_material'] += 1
                    # Registra os nomes tentados para o relatório
                    if type_name:
                        materiais_faltantes.add("{} - {}".format(abbrev, type_name))
                    else:
                        materiais_faltantes.add(abbrev)
                    continue

                # Pinta tubo
                faces_count = paint_pipe_faces(pipe, material)
                if faces_count > 0:
                    stats['coloridos'] += 1
                    stats['faces_pintadas'] += faces_count
                    if usou_fallback:
                        stats['coloridos_fallback'] += 1
                    else:
                        stats['coloridos_combinado'] += 1

            except Exception as e:
                stats['erro'] += 1

        t.Commit()

    except Exception as e:
        t.RollBack()
        output.print_md("\n❌ **ERRO:** {}".format(str(e)))
        forms.alert("Erro ao processar tubos: {}".format(str(e)), exitscript=True)

    # Relatório final
    output.print_md("\n---")
    output.print_md("## ✅ RELATÓRIO FINAL")
    output.print_md("---")
    output.print_md("**Total de tubos:** {}".format(stats['total']))
    output.print_md("**✓ Tubos coloridos:** {}".format(stats['coloridos']))
    output.print_md("**✓ Faces pintadas:** {}".format(stats['faces_pintadas']))

    if stats['coloridos_combinado'] > 0:
        output.print_md("  ↳ **Por Abreviatura + Tipo:** {}".format(stats['coloridos_combinado']))

    if stats['coloridos_fallback'] > 0:
        output.print_md("  ↳ **Por Abreviatura (fallback):** {}".format(stats['coloridos_fallback']))

    if stats['limpos'] > 0:
        output.print_md("**🧹 Tubos limpos:** {}".format(stats['limpos']))

    if stats['sem_abreviatura'] > 0:
        output.print_md("**⚠ Sem abreviatura:** {}".format(stats['sem_abreviatura']))

    if stats['sem_material'] > 0:
        output.print_md("**⚠ Sem material:** {}".format(stats['sem_material']))
        output.print_md("\n**Materiais faltantes (nenhuma tentativa encontrou material):**")
        for mat_name in sorted(materiais_faltantes):
            output.print_md("  - {}".format(mat_name))

    if stats['erro'] > 0:
        output.print_md("**❌ Erros:** {}".format(stats['erro']))

    # Instruções finais
    if materiais_faltantes:
        output.print_md("\n---")
        output.print_md("### 📋 INSTRUÇÕES")
        output.print_md("Crie os seguintes materiais no Revit para cobertura completa:")
        for mat_name in sorted(materiais_faltantes):
            output.print_md("  1. **{}**".format(mat_name))
        output.print_md("\n> 💡 Dica: Você também pode criar apenas **{}** para usar como fallback.".format("Abreviatura"))


# __  __      _      ___  _   _
# |  \/  |    / \    |_ _|| \ | |
# | |\/| |   / _ \    | | |  \| |
# | |  | |  / ___ \   | | | |\  |
# |_|  |_| /_/   \_\ |___||_| \_|

# Executa
if __name__ == '__main__':
    main()