# -*- coding: utf-8 -*-
#__title__ = "FiltrosDeVista: Copiar para Outra Vista"
__title__ = "CopiarFiltrosDeVista"
__author__ = "Alexjr"
__version__ = "Versão: 1.2"
__doc__ = """Versão = 1.2
Data    = 05.03.2026
_____________________________________________________________________
Descrição:

Copia Filtros de outra Vista/Modelo de Vista com opção
de adicionar ou substituir os filtros existentes.
Opções para copiar também:
- Substituições Gráficas (graphic overrides)
- Visibilidade (mostrar/ocultar)
- Ativado (ativo/inativo)
- Meio-Tom (halftone)
_____________________________________________________________________
Como usar:

-> Clique no botão
-> Selecione a Vista/Modelo de Vista de origem
-> Selecione os Filtros
-> Escolha quais configurações copiar
-> Selecione as Vistas/Modelos de Vista de destino
_____________________________________________________________________
Última atualização:
[05.03.2026] - 1.2 Release - Removida dependência GUI.forms,
               reescrito usando apenas pyrevit.forms.
               Adicionadas opções de Visibilidade, Ativado e Meio-Tom.
[17.01.2023] - 1.1 Release
[22.09.2022] - 1.0 Release
_____________________________________________________________________
Autor: Erik Frits"""

# ╦╔╦╗╔═╗╔═╗╦═╗╔╦╗╔═╗
# ║║║║╠═╝║ ║╠╦╝ ║ ╚═╗
# ╩╩ ╩╩  ╚═╝╩╚═ ╩ ╚═╝ IMPORTS
# ==============================================================================
import traceback
from Autodesk.Revit.DB import (
    FilteredElementCollector, BuiltInCategory, ViewType, Transaction
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


def _views_with_filters(views):
    """Retorna apenas vistas/modelos que possuem pelo menos um filtro aplicado."""
    result = []
    for v in views:
        try:
            if v.GetFilters():
                result.append(v)
        except Exception:
            pass
    return result


# ==============================================================================
# PASSO 1 - Selecionar vista / modelo de vista de origem
# ==============================================================================
all_views = _get_all_views()
src_candidates = _views_with_filters(all_views)

if not src_candidates:
    forms.alert(
        "Nenhuma Vista ou Modelo de Vista com Filtros encontrado.\n"
        "Aplique pelo menos um Filtro de Vista e tente novamente.",
        exitscript=True
    )

# Perguntar quais tipos exibir na lista de origem
show_type = forms.CommandSwitchWindow.show(
    ['Vistas + Modelos de Vista', 'Somente Vistas', 'Somente Modelos de Vista'],
    message='Passo 1 de 4 - Filtrar lista de origem por tipo:'
)

if show_type is None:
    forms.alert("Operação cancelada.", exitscript=True)

if show_type == 'Somente Vistas':
    src_candidates_filtered = [v for v in src_candidates if not v.IsTemplate]
elif show_type == 'Somente Modelos de Vista':
    src_candidates_filtered = [v for v in src_candidates if v.IsTemplate]
else:
    src_candidates_filtered = src_candidates

if not src_candidates_filtered:
    forms.alert(
        "Nenhum item encontrado para o tipo selecionado.\n"
        "Tente uma opção diferente.",
        exitscript=True
    )

src_label_map = {_view_label(v): v for v in src_candidates_filtered}

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
# PASSO 2 - Selecionar filtros da vista de origem
# ==============================================================================
try:
    if app_year >= 2021:
        filter_ids = src_view.GetOrderedFilters()
    else:
        filter_ids = src_view.GetFilters()
except Exception:
    filter_ids = src_view.GetFilters()

src_filters = [doc.GetElement(fid) for fid in filter_ids]
filter_label_map = {f.Name: f for f in src_filters}

chosen_filter_names = forms.SelectFromList.show(
    sorted(filter_label_map.keys()),
    title='{} - Passo 2 de 4'.format(__title__),
    prompt='Selecione os Filtros a copiar:',
    multiselect=True
)

if not chosen_filter_names:
    forms.alert("Nenhum filtro selecionado. Encerrando.", exitscript=True)

selected_filters = [filter_label_map[n] for n in chosen_filter_names]

# ==============================================================================
# PASSO 3 - Escolher quais configurações copiar
# ==============================================================================
OPT_CLEAR   = 'Limpar TODOS os filtros do destino antes de copiar'
settings_options = [
    'Substituições Gráficas',
    'Visibilidade (mostrar/ocultar)',
    'Ativado (ativo/inativo)',
    'Meio-Tom',
    OPT_CLEAR,
]

# As 4 primeiras opções ficam marcadas por padrão; o clear fica desmarcado
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

copy_overrides  = 'Substituições Gráficas'        in chosen_settings
copy_visibility = 'Visibilidade (mostrar/ocultar)' in chosen_settings
copy_enabled    = 'Ativado (ativo/inativo)'        in chosen_settings
copy_halftone   = 'Meio-Tom'                       in chosen_settings
clear_dest      = OPT_CLEAR                        in chosen_settings

# Confirmação extra se o usuário optou por limpar os filtros do destino
if clear_dest:
    confirm = forms.alert(
        "Atencao!\n\n"
        "A opcao 'Limpar TODOS os filtros do destino' ira remover "
        "todos os filtros existentes nas vistas de destino antes de copiar.\n\n"
        "Deseja continuar?",
        yes=True, no=True
    )
    if not confirm:
        forms.alert("Operacao cancelada.", exitscript=True)

# ==============================================================================
# PASSO 4 - Selecionar vistas / modelos de vista de destino
# ==============================================================================
all_views_refreshed = _get_all_views()

# Perguntar quais tipos exibir na lista de destino
show_type_dest = forms.CommandSwitchWindow.show(
    ['Vistas + Modelos de Vista', 'Somente Vistas', 'Somente Modelos de Vista'],
    message='Passo 4 de 4 - Filtrar lista de destino por tipo:'
)

if show_type_dest is None:
    forms.alert("Operação cancelada.", exitscript=True)

if show_type_dest == 'Somente Vistas':
    dest_candidates = [v for v in all_views_refreshed if not v.IsTemplate]
elif show_type_dest == 'Somente Modelos de Vista':
    dest_candidates = [v for v in all_views_refreshed if v.IsTemplate]
else:
    dest_candidates = all_views_refreshed

if not dest_candidates:
    forms.alert(
        "Nenhum item encontrado para o tipo selecionado.\n"
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
print('*** Filtros Selecionados:')
for f in selected_filters:
    print('    - {}'.format(f.Name))

print('\n*** Configurações a copiar:')
print('    Substituições Gráficas     : {}'.format(copy_overrides))
print('    Visibilidade               : {}'.format(copy_visibility))
print('    Ativado                    : {}'.format(copy_enabled))
print('    Meio-Tom                   : {}'.format(copy_halftone))
print('    Limpar filtros do destino  : {}'.format(clear_dest))

t = Transaction(doc, __title__)
t.Start()

try:
    print('\n*** Vistas / Modelos de Vista de Destino:')
    for view in dest_views:
        print('\n  -> {}'.format(view.Name))

        # Limpar todos os filtros do destino antes de copiar
        if clear_dest:
            for fid in list(view.GetFilters()):
                try:
                    view.RemoveFilter(fid)
                except Exception:
                    pass
            print('     [LIMPO] Todos os filtros removidos.')

        # IDs dos filtros já presentes na vista de destino
        existing_ids = set(view.GetFilters())

        for f_elem in selected_filters:
            try:
                f_id = f_elem.Id

                # Adiciona o filtro à vista de destino se ainda não estiver presente
                if f_id not in existing_ids:
                    view.AddFilter(f_id)
                    existing_ids.add(f_id)
                    print('     [ADICIONADO]  {}'.format(f_elem.Name))
                else:
                    print('     [JÁ EXISTE]   {}'.format(f_elem.Name))

                # --- Substituições Gráficas ---
                if copy_overrides:
                    ogs = src_view.GetFilterOverrides(f_id)
                    view.SetFilterOverrides(f_id, ogs)

                # --- Visibilidade ---
                if copy_visibility:
                    vis = src_view.GetFilterVisibility(f_id)
                    view.SetFilterVisibility(f_id, vis)

                # --- Ativado ---
                if copy_enabled:
                    ena = src_view.GetIsFilterEnabled(f_id)
                    view.SetIsFilterEnabled(f_id, ena)

                # --- Meio-Tom (independente, apenas quando Substituições NÃO é copiado) ---
                # Quando copy_overrides é True, o meio-tom já está incluído
                # dentro do OverrideGraphicSettings copiado acima.
                if copy_halftone and not copy_overrides:
                    src_ogs  = src_view.GetFilterOverrides(f_id)
                    dest_ogs = view.GetFilterOverrides(f_id)
                    dest_ogs.SetHalftone(src_ogs.Halftone)
                    view.SetFilterOverrides(f_id, dest_ogs)

            except Exception:
                print('     [ERRO] {} :\n{}'.format(f_elem.Name, traceback.format_exc()))

    t.Commit()
    print('\nExecução Concluída com Sucesso.')

except Exception:
    t.RollBack()
    print('[TRANSAÇÃO REVERTIDA]\n{}'.format(traceback.format_exc()))