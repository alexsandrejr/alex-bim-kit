# -*- coding: utf-8 -*-
#__title__ = "CategoriasDeModelo: Copiar para Outra Vista"
__title__ = "CopiarCategoriasDeModelo"
__author__ = "Alexjr"
__version__ = "Versão: 1.0"
__doc__ = """Versão = 1.0
Data    = 05.03.2026
_____________________________________________________________________
Descrição:

Copia as configurações de Categorias de Modelo de uma
Vista/Modelo de Vista para outras, com controle total sobre
quais configurações serão copiadas:
- Visibilidade (mostrar/ocultar)
- Substituições Gráficas de Projeção (cor, espessura, padrão)
- Substituições Gráficas de Corte (cor, espessura, padrão)
- Meio-Tom
- Detalhe
_____________________________________________________________________
Como usar:

-> Clique no botão
-> Filtre por tipo (Vistas / Modelos de Vista)
-> Selecione a Vista/Modelo de Vista de origem
-> Selecione as Categorias de Modelo a copiar
-> Escolha quais configurações copiar
-> Filtre por tipo e selecione as Vistas/Modelos de Vista de destino
_____________________________________________________________________
Versão: 1.0 Release
_____________________________________________________________________
"""

# ╦╔╦╗╔═╗╔═╗╦═╗╔╦╗╔═╗
# ║║║║╠═╝║ ║╠╦╝ ║ ╚═╗
# ╩╩ ╩╩  ╚═╝╩╚═ ╩ ╚═╝ IMPORTS
# ==============================================================================
import traceback
from Autodesk.Revit.DB import (
    FilteredElementCollector, BuiltInCategory, ViewType, Transaction,
    Category, OverrideGraphicSettings, CategoryType
)
from pyrevit import forms, script

# ==============================================================================
# VARIÁVEIS
# ==============================================================================
uidoc    = __revit__.ActiveUIDocument
app      = __revit__.Application
doc      = __revit__.ActiveUIDocument.Document
app_year = int(app.VersionNumber)
output   = script.get_output()

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================

def _view_label(view):
    """Retorna um rótulo de exibição como '[PLANTA] Nível 1' para uma vista."""
    type_map = {
        ViewType.FloorPlan:       '[PLANTA]',
        ViewType.CeilingPlan:     '[TETO]',
        ViewType.ThreeD:          '[3D]',
        ViewType.Section:         '[CORTE]',
        ViewType.Elevation:       '[ELEV]',
        ViewType.DraftingView:    '[RASCUNHO]',
        ViewType.AreaPlan:        '[ÁREA]',
        ViewType.Rendering:       '[CÂMERA]',
        ViewType.Legend:          '[LEGENDA]',
        ViewType.EngineeringPlan: '[ESTRT]',
        ViewType.Walkthrough:     '[PERCURSO]',
    }
    prefix = type_map.get(view.ViewType, '[?]')
    suffix = ' [MODELO DE VISTA]' if view.IsTemplate else ''
    return '{} {}{}'.format(prefix, view.Name, suffix)


def _get_all_views():
    return list(
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_Views)
        .ToElements()
    )


def _filter_views_by_type(views, show_type):
    """Filtra lista de vistas conforme a escolha do usuário."""
    if show_type == 'Somente Vistas':
        return [v for v in views if not v.IsTemplate]
    elif show_type == 'Somente Modelos de Vista':
        return [v for v in views if v.IsTemplate]
    return views


def _get_model_categories(view=None):
    """Retorna dict {nome: Category} das categorias de modelo do V/G.
    Usa BuiltInCategory para garantir compatibilidade com IronPython/Revit."""
    from Autodesk.Revit.DB import BuiltInCategory, ElementId
    import System

    cats = {}

    # Itera todos os valores do enum BuiltInCategory
    for bic in System.Enum.GetValues(BuiltInCategory):
        try:
            cat_id = ElementId(int(bic))
            if cat_id.IntegerValue >= 0:
                continue  # categorias de modelo tem Id negativo no enum BIC
            cat = doc.Settings.Categories.get_Item(bic)
            if cat is None:
                continue
            if cat.CategoryType != CategoryType.Model:
                continue
            if view is not None:
                try:
                    if not cat.AllowsVisibilityControl(view):
                        continue
                except Exception:
                    pass
            cats[cat.Name] = cat
        except Exception:
            pass
    return cats


def _ask_view_type_filter(step_label):
    """Exibe CommandSwitchWindow para filtrar tipo de vista."""
    show_type = forms.CommandSwitchWindow.show(
        ['Vistas + Modelos de Vista', 'Somente Vistas', 'Somente Modelos de Vista'],
        message='{} - Filtrar lista por tipo:'.format(step_label)
    )
    if show_type is None:
        forms.alert("Operação cancelada.", exitscript=True)
    return show_type


# ==============================================================================
# PASSO 1 - Selecionar vista / modelo de vista de origem
# ==============================================================================
all_views = _get_all_views()

show_type_src = _ask_view_type_filter('Passo 1 de 4')
src_candidates = _filter_views_by_type(all_views, show_type_src)

if not src_candidates:
    forms.alert(
        "Nenhuma Vista ou Modelo de Vista encontrado para o tipo selecionado.\n"
        "Tente uma opção diferente.",
        exitscript=True
    )

src_label_map = {_view_label(v): v for v in src_candidates}

chosen_src_label = forms.SelectFromList.show(
    sorted(src_label_map.keys()),
    title='{} - Passo 1 de 4'.format(__title__),
    prompt='Selecione a Vista / Modelo de Vista de origem:',
    multiselect=False
)

if not chosen_src_label:
    forms.alert("Nenhuma vista de origem selecionada. Encerrando.", exitscript=True)

src_view = src_label_map[chosen_src_label]

# ==============================================================================
# PASSO 2 - Selecionar categorias de modelo
# ==============================================================================
all_model_cats = _get_model_categories(view=src_view)

if not all_model_cats:
    forms.alert("Nenhuma Categoria de Modelo encontrada no documento.", exitscript=True)

chosen_cat_names = forms.SelectFromList.show(
    sorted(all_model_cats.keys()),
    title='{} - Passo 2 de 4'.format(__title__),
    prompt='Selecione as Categorias de Modelo a copiar:',
    multiselect=True
)

if not chosen_cat_names:
    forms.alert("Nenhuma categoria selecionada. Encerrando.", exitscript=True)

selected_cats = [all_model_cats[n] for n in chosen_cat_names]

# ==============================================================================
# PASSO 3 - Escolher quais configurações copiar
# ==============================================================================
OPT_VISIBILITY   = 'Visibilidade (mostrar/ocultar)'
OPT_PROJ         = 'Substituições Gráficas - Projeção (cor, espessura, padrão)'
OPT_CUT          = 'Substituições Gráficas - Corte (cor, espessura, padrão)'
OPT_HALFTONE     = 'Meio-Tom'
OPT_DETAIL       = 'Nível de Detalhe'
OPT_CLEAR        = 'Limpar substituições das categorias no destino antes de copiar'

settings_options = [
    OPT_VISIBILITY,
    OPT_PROJ,
    OPT_CUT,
    OPT_HALFTONE,
    OPT_DETAIL,
    OPT_CLEAR,
]

# Todas marcadas por padrão, exceto o clear
default_settings = [o for o in settings_options if o != OPT_CLEAR]

chosen_settings = forms.SelectFromList.show(
    settings_options,
    title='{} - Passo 3 de 4'.format(__title__),
    prompt='Selecione quais configurações copiar:',
    multiselect=True,
    default=default_settings
)

if chosen_settings is None:
    forms.alert("Nenhuma configuração selecionada. Encerrando.", exitscript=True)

copy_visibility = OPT_VISIBILITY in chosen_settings
copy_proj       = OPT_PROJ       in chosen_settings
copy_cut        = OPT_CUT        in chosen_settings
copy_halftone   = OPT_HALFTONE   in chosen_settings
copy_detail     = OPT_DETAIL     in chosen_settings
clear_dest      = OPT_CLEAR      in chosen_settings

# Confirmação extra se o usuário optou por limpar
if clear_dest:
    confirm = forms.alert(
        "Atenção!\n\n"
        "A opção 'Limpar substituições das categorias no destino' irá resetar "
        "todas as substituições gráficas das categorias selecionadas "
        "nas vistas de destino antes de copiar.\n\n"
        "Deseja continuar?",
        yes=True, no=True
    )
    if not confirm:
        forms.alert("Operação cancelada.", exitscript=True)

# ==============================================================================
# PASSO 4 - Selecionar vistas / modelos de vista de destino
# ==============================================================================
all_views_refreshed = _get_all_views()

show_type_dest = _ask_view_type_filter('Passo 4 de 4')
dest_candidates = _filter_views_by_type(all_views_refreshed, show_type_dest)

if not dest_candidates:
    forms.alert(
        "Nenhuma Vista ou Modelo de Vista encontrado para o tipo selecionado.\n"
        "Tente uma opção diferente.",
        exitscript=True
    )

dest_label_map = {_view_label(v): v for v in dest_candidates}

chosen_dest_labels = forms.SelectFromList.show(
    sorted(dest_label_map.keys()),
    title='{} - Passo 4 de 4'.format(__title__),
    prompt='Selecione as Vistas / Modelos de Vista de destino:',
    multiselect=True
)

if not chosen_dest_labels:
    forms.alert("Nenhuma vista de destino selecionada. Encerrando.", exitscript=True)

dest_views = [dest_label_map[lbl] for lbl in chosen_dest_labels]

# ==============================================================================
# EXECUÇÃO
# ==============================================================================
print('*** Vista de Origem: {} ***'.format(src_view.Name))
print('*** Categorias Selecionadas:')
for cat in selected_cats:
    print('    - {}'.format(cat.Name))

print('\n*** Configurações a copiar:')
print('    Visibilidade              : {}'.format(copy_visibility))
print('    Subst. Gráficas Projeção  : {}'.format(copy_proj))
print('    Subst. Gráficas Corte     : {}'.format(copy_cut))
print('    Meio-Tom                  : {}'.format(copy_halftone))
print('    Nível de Detalhe          : {}'.format(copy_detail))
print('    Limpar destino            : {}'.format(clear_dest))

t = Transaction(doc, __title__)
t.Start()

try:
    print('\n*** Vistas / Modelos de Vista de Destino:')
    for view in dest_views:
        print('\n  -> {}'.format(view.Name))

        for cat in selected_cats:
            try:
                cat_id = cat.Id

                # --- Limpar substituições antes de copiar ---
                if clear_dest:
                    view.SetCategoryOverrides(cat_id, OverrideGraphicSettings())
                    print('     [LIMPO]  {}'.format(cat.Name))

                # --- Visibilidade ---
                if copy_visibility:
                    vis = src_view.GetCategoryHidden(cat_id)
                    view.SetCategoryHidden(cat_id, vis)

                # --- Substituições Gráficas (Projeção e/ou Corte) ---
                if copy_proj or copy_cut or copy_halftone:
                    src_ogs  = src_view.GetCategoryOverrides(cat_id)
                    dest_ogs = view.GetCategoryOverrides(cat_id)

                    if copy_proj:
                        # Linhas de projeção
                        dest_ogs.SetProjectionLineColor(src_ogs.ProjectionLineColor)
                        dest_ogs.SetProjectionLineWeight(src_ogs.ProjectionLineWeight)
                        dest_ogs.SetProjectionLinePatternId(src_ogs.ProjectionLinePatternId)
                        # Padrão de superfície de projeção
                        dest_ogs.SetSurfaceForegroundPatternColor(src_ogs.SurfaceForegroundPatternColor)
                        dest_ogs.SetSurfaceForegroundPatternId(src_ogs.SurfaceForegroundPatternId)
                        dest_ogs.SetSurfaceForegroundPatternVisible(src_ogs.IsSurfaceForegroundPatternVisible)
                        dest_ogs.SetSurfaceBackgroundPatternColor(src_ogs.SurfaceBackgroundPatternColor)
                        dest_ogs.SetSurfaceBackgroundPatternId(src_ogs.SurfaceBackgroundPatternId)
                        dest_ogs.SetSurfaceBackgroundPatternVisible(src_ogs.IsSurfaceBackgroundPatternVisible)
                        dest_ogs.SetSurfaceTransparency(src_ogs.Transparency)

                    if copy_cut:
                        # Linhas de corte
                        dest_ogs.SetCutLineColor(src_ogs.CutLineColor)
                        dest_ogs.SetCutLineWeight(src_ogs.CutLineWeight)
                        dest_ogs.SetCutLinePatternId(src_ogs.CutLinePatternId)
                        # Padrão de superfície de corte
                        dest_ogs.SetCutForegroundPatternColor(src_ogs.CutForegroundPatternColor)
                        dest_ogs.SetCutForegroundPatternId(src_ogs.CutForegroundPatternId)
                        dest_ogs.SetCutForegroundPatternVisible(src_ogs.IsCutForegroundPatternVisible)
                        dest_ogs.SetCutBackgroundPatternColor(src_ogs.CutBackgroundPatternColor)
                        dest_ogs.SetCutBackgroundPatternId(src_ogs.CutBackgroundPatternId)
                        dest_ogs.SetCutBackgroundPatternVisible(src_ogs.IsCutBackgroundPatternVisible)

                    if copy_halftone:
                        dest_ogs.SetHalftone(src_ogs.Halftone)

                    view.SetCategoryOverrides(cat_id, dest_ogs)

                # --- Nível de Detalhe ---
                if copy_detail:
                    detail = src_view.GetCategoryOverrides(cat_id).DetailLevel
                    ogs_detail = view.GetCategoryOverrides(cat_id)
                    ogs_detail.SetDetailLevel(detail)
                    view.SetCategoryOverrides(cat_id, ogs_detail)

                print('     [OK]     {}'.format(cat.Name))

            except Exception:
                print('     [ERRO]   {} :\n{}'.format(cat.Name, traceback.format_exc()))

    t.Commit()
    print('\nExecução Concluída com Sucesso.')

except Exception:
    t.RollBack()
    print('[TRANSAÇÃO REVERTIDA]\n{}'.format(traceback.format_exc()))