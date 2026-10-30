# -*- coding: utf-8 -*-
from pyrevit import revit, forms
from Autodesk.Revit.DB import FilteredElementCollector, Transaction, StorageType
import re

doc = revit.doc
view = doc.ActiveView


def natural_key(s):
    """Ordenação natural: 'A2' vem antes de 'A10'."""
    if s is None:
        s = ""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", str(s))]


def get_param_as_string(param):
    if not param:
        return None
    # Prioriza AsString; se não tiver, tenta ValueString
    try:
        val = param.AsString()
        if val is not None:
            return val
    except:
        pass
    try:
        return param.AsValueString()
    except:
        return None


def get_description_value_auto(elem, desc_param_name):
    """Tenta ler descrição como INSTÂNCIA; se não der, tenta como TIPO."""
    # 1) instância
    p_inst = elem.LookupParameter(desc_param_name)
    val = get_param_as_string(p_inst)
    if val is not None and str(val).strip() != "":
        return str(val).strip()

    # 2) tipo
    try:
        etype = doc.GetElement(elem.GetTypeId())
        if etype:
            p_type = etype.LookupParameter(desc_param_name)
            val2 = get_param_as_string(p_type)
            if val2 is not None and str(val2).strip() != "":
                return str(val2).strip()
    except:
        pass

    return None


def set_string_parameter(elem, param_name, value):
    """Define parâmetro (texto) se existir e não for somente leitura."""
    p = elem.LookupParameter(param_name)
    if not p:
        return False, "Parâmetro não encontrado"
    if p.IsReadOnly:
        return False, "Parâmetro somente leitura"
    try:
        p.Set(str(value))
        return True, None
    except Exception as ex:
        return False, str(ex)


def collect_param_names_from_elements(elements, include_instance=True, include_type=True):
    """Retorna dict com nomes de parâmetros e contagem de ocorrência.
    keys: (name, scope) onde scope = 'Instância' ou 'Tipo'
    """
    found = {}  # (name, scope) -> count

    for e in elements:
        if include_instance:
            try:
                for p in e.Parameters:
                    if p and p.Definition:
                        key = (p.Definition.Name, "Instância")
                        found[key] = found.get(key, 0) + 1
            except:
                pass

        if include_type:
            try:
                etype = doc.GetElement(e.GetTypeId())
                if etype:
                    for p in etype.Parameters:
                        if p and p.Definition:
                            key = (p.Definition.Name, "Tipo")
                            found[key] = found.get(key, 0) + 1
            except:
                pass

    return found


def collect_writable_string_params(elements):
    """Lista nomes de parâmetros (instância) adequados para escrita de texto."""
    counts = {}
    for e in elements:
        try:
            for p in e.Parameters:
                if not p or not p.Definition:
                    continue
                if p.IsReadOnly:
                    continue
                if p.StorageType != StorageType.String:
                    continue
                name = p.Definition.Name
                counts[name] = counts.get(name, 0) + 1
        except:
            pass
    return counts


class ParamChoice(object):
    def __init__(self, name, scope=None, count=None):
        self.name = name
        self.scope = scope
        self.count = count

    @property
    def display(self):
        bits = [self.name]
        if self.scope:
            bits.append(u"({})".format(self.scope))
        if self.count is not None:
            bits.append(u"[{}]".format(self.count))
        return u"  —  ".join(bits)

    def __str__(self):
        return self.display


# ---------------- UI ----------------
prefix = forms.ask_for_string(
    default="E",
    prompt="Prefixo (ex.: E)",
    title="Numeração automática - Prefixo"
)
if prefix is None:
    forms.alert("Cancelado.", exitscript=True)

# Coletar elementos na vista ativa (uma vez)
elements = list(FilteredElementCollector(doc, view.Id).WhereElementIsNotElementType())
if not elements:
    forms.alert("Nenhum elemento encontrado na vista ativa.", exitscript=True)

# Combobox: parâmetro de SAÍDA (texto + editável, instância)
out_counts = collect_writable_string_params(elements)
out_items = [ParamChoice(n, "Instância", c) for n, c in out_counts.items()]
out_items.sort(key=lambda x: x.name.lower())

out_choice = forms.SelectFromList.show(
    out_items,
    name_attr="display",
    title="Selecione o parâmetro de SAÍDA (onde será gravado E1, E2...)",
    button_name="Selecionar"
)
if not out_choice:
    forms.alert("Cancelado.", exitscript=True)
out_param_name = out_choice.name

# Combobox: parâmetro de DESCRIÇÃO (instância + tipo)
desc_found = collect_param_names_from_elements(elements, include_instance=True, include_type=True)
desc_items = [ParamChoice(n, scope, c) for (n, scope), c in desc_found.items()]
desc_items.sort(key=lambda x: (x.name.lower(), x.scope))

desc_choice = forms.SelectFromList.show(
    desc_items,
    name_attr="display",
    title="Selecione o parâmetro de DESCRIÇÃO (agrupamento)",
    button_name="Selecionar"
)
if not desc_choice:
    forms.alert("Cancelado.", exitscript=True)
desc_param_name = desc_choice.name


# ---------------- PROCESSAMENTO ----------------
# Agrupar por descrição
groups = {}  # desc -> [elems]
missing_desc = 0

for e in elements:
    desc = get_description_value_auto(e, desc_param_name)
    if desc is None or str(desc).strip() == "":
        missing_desc += 1
        continue
    groups.setdefault(desc, []).append(e)

if not groups:
    forms.alert(
        "Não foi possível formar grupos.\n"
        "Verifique se o parâmetro de descrição existe e tem valores na vista.",
        exitscript=True
    )

# Ordenar chaves e numerar
sorted_keys = sorted(groups.keys(), key=natural_key)
start_index = 1  # E1, E2, E3...

written = 0
failed = 0
fail_reasons = {}

t = Transaction(doc, "Numeração automática (pyRevit)")
t.Start()
try:
    idx = start_index
    for k in sorted_keys:
        tag = "{}{}".format(prefix, idx)
        for e in groups[k]:
            ok, err = set_string_parameter(e, out_param_name, tag)
            if ok:
                written += 1
            else:
                failed += 1
                fail_reasons[err] = fail_reasons.get(err, 0) + 1
        idx += 1
finally:
    t.Commit()

# Relatório
msg = []
msg.append("Vista: {}".format(view.Name))
msg.append("Elementos na vista: {}".format(len(elements)))
msg.append("Grupos por descrição: {}".format(len(sorted_keys)))
msg.append("Sem descrição (ignorados): {}".format(missing_desc))
msg.append("Atualizados com sucesso: {}".format(written))
msg.append("Falhas: {}".format(failed))

if fail_reasons:
    msg.append("\nPrincipais motivos de falha:")
    for r, c in sorted(fail_reasons.items(), key=lambda x: x[1], reverse=True):
        msg.append("- {}: {}".format(r, c))

forms.alert("\n".join(msg), title="Numeração automática - Resultado")
