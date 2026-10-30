# -*- coding: utf-8 -*-
__title__ = "Duplicador de Vistas"
__author__ = "AlexJR"
__version__ = "Versão 1.0"
__doc__ = """
_____________________________________________________________________
Descrição:
Duplica múltiplas vistas do projeto de forma automatizada com opções 
de renomeação em lote. Permite selecionar vistas através de checkboxes, 
escolher o modo de duplicação (Duplicate, With Detailing ou As Dependent), 
e aplicar prefixos, sufixos ou substituição de texto nos nomes das novas 
vistas. Ideal para criar variações de vistas de forma rápida e organizada.
_____________________________________________________________________
"""
from pyrevit import forms
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument


def get_views():
    """Retorna lista de vistas válidas (não templates) ordenadas por nome"""
    views = FilteredElementCollector(doc).OfClass(View).ToElements()
    valid = []
    for v in views:
        if not v.IsTemplate and v.CanViewBeDuplicated(ViewDuplicateOption.Duplicate):
            valid.append(v)
    return sorted(valid, key=lambda x: x.Name)


views = get_views()

if not views:
    forms.alert("Nenhuma vista disponível para duplicar.", title="Aviso")
    raise SystemExit()


class DuplicateDialog(forms.WPFWindow):
    def __init__(self):
        forms.WPFWindow.__init__(self, 'duplicator.xaml')

        # Preencher lista de vistas com checkboxes
        self.view_items = []
        for v in views:
            item = {
                'view': v,
                'name': v.Name,
                'type': str(v.ViewType),
                'checked': False
            }
            self.view_items.append(item)

        # Atualizar lista visual
        self.update_view_list()

        # Conectar eventos dos botões de seleção
        self.selectAllBtn.Click += self.on_select_all
        self.selectNoneBtn.Click += self.on_select_none

        # Conectar duplo clique na lista
        self.viewslist.MouseDoubleClick += self.on_view_list_click

    def update_view_list(self):
        """Atualiza a lista visual de vistas"""
        self.viewslist.Items.Clear()
        for item in self.view_items:
            checkbox_text = "[X] " if item['checked'] else "[ ] "
            display_text = "{}{}   [{}]".format(checkbox_text, item['name'], item['type'])
            self.viewslist.Items.Add(display_text)

    def on_view_list_click(self, sender, args):
        """Toggle checkbox quando dar duplo clique em um item"""
        if self.viewslist.SelectedIndex >= 0:
            idx = self.viewslist.SelectedIndex
            self.view_items[idx]['checked'] = not self.view_items[idx]['checked']
            self.update_view_list()
            self.viewslist.SelectedIndex = idx

    def on_click_ok(self, sender, args):
        """Executar duplicação sem fechar"""
        print("Botão OK clicado")  # Debug
        self.duplicate_views()

    def on_click_cancel(self, sender, args):
        """Cancelar e fechar diálogo"""
        print("Botão Cancelar clicado")  # Debug
        self.DialogResult = False
        self.Close()

    def on_select_all(self, sender, args):
        """Selecionar todas as vistas"""
        for item in self.view_items:
            item['checked'] = True
        self.update_view_list()

    def on_select_none(self, sender, args):
        """Desselecionar todas as vistas"""
        for item in self.view_items:
            item['checked'] = False
        self.update_view_list()

    def duplicate_views(self):
        """Executa a duplicação das vistas selecionadas"""
        # ------------------------------------------------------------
        # VALIDAR SELEÇÃO - USAR CHECKBOXES
        # ------------------------------------------------------------
        selected_views = [item['view'] for item in self.view_items if item['checked']]

        print("Vistas selecionadas:", len(selected_views))  # Debug

        if not selected_views:
            forms.alert("Nenhuma vista selecionada!", title="Erro")
            return

        # ------------------------------------------------------------
        # DEFINIR MODO DE DUPLICAÇÃO
        # ------------------------------------------------------------
        if self.optDuplicate.IsChecked:
            dup_option = ViewDuplicateOption.Duplicate
            print("Modo: Duplicate")
        elif self.optWithDetail.IsChecked:
            dup_option = ViewDuplicateOption.WithDetailing
            print("Modo: WithDetailing")
        elif self.optDependent.IsChecked:
            dup_option = ViewDuplicateOption.AsDependent
            print("Modo: AsDependent")
        else:
            forms.alert("Escolha uma opção de duplicação.", title="Erro")
            return

        # ------------------------------------------------------------
        # OBTER PARÂMETROS DE RENOMEAÇÃO
        # ------------------------------------------------------------
        replace_from = self.replaceFrom.Text.strip() if self.replaceFrom.Text else ""
        replace_to = self.replaceTo.Text.strip() if self.replaceTo.Text else ""
        prefix = self.prefixTxt.Text.strip() if self.prefixTxt.Text else ""
        suffix = self.suffixTxt.Text.strip() if self.suffixTxt.Text else ""

        print("Replace: '{}' -> '{}'".format(replace_from, replace_to))  # Debug
        print("Prefix: '{}', Suffix: '{}'".format(prefix, suffix))  # Debug

        # ------------------------------------------------------------
        # EXECUTAR DUPLICAÇÃO COM TRATAMENTO DE ERROS
        # ------------------------------------------------------------
        t = Transaction(doc, "Duplicar Vistas")
        t.Start()

        success_count = 0
        error_count = 0
        error_messages = []

        try:
            for original in selected_views:
                print("Processando vista:", original.Name)  # Debug

                try:
                    # Verificar se a vista pode ser duplicada com a opção escolhida
                    if not original.CanViewBeDuplicated(dup_option):
                        error_messages.append("'{}' não pode ser duplicada com esta opção".format(original.Name))
                        error_count += 1
                        continue

                    print("Duplicando vista:", original.Name)  # Debug
                    new_id = original.Duplicate(dup_option)
                    new_view = doc.GetElement(new_id)
                    print("Vista duplicada com ID:", new_id)  # Debug

                    # Construir novo nome
                    new_name = original.Name

                    # Aplicar Replace From / To
                    if replace_from:
                        new_name = new_name.replace(replace_from, replace_to)

                    # Aplicar Prefixo e Sufixo
                    new_name = prefix + new_name + suffix

                    # Garantir nome único
                    attempt = 0
                    base_name = new_name
                    while True:
                        try:
                            new_view.Name = new_name
                            print("Vista renomeada para:", new_name)  # Debug
                            break
                        except:
                            attempt += 1
                            new_name = "{}_{}".format(base_name, attempt)
                            if attempt > 100:
                                raise Exception("Não foi possível encontrar nome único")

                    success_count += 1

                except Exception as e:
                    error_msg = "Erro em '{}': {}".format(original.Name, str(e))
                    print(error_msg)  # Debug
                    error_messages.append(error_msg)
                    error_count += 1

            t.Commit()
            print("Transação commitada")  # Debug

        except Exception as e:
            t.RollBack()
            error_msg = "Erro durante a transação: {}".format(str(e))
            print(error_msg)  # Debug
            forms.alert(error_msg, title="Erro")
            return

        # ------------------------------------------------------------
        # RELATÓRIO FINAL
        # ------------------------------------------------------------
        message = "Duplicação concluída!\n\n"
        message += "Vistas duplicadas: {}\n".format(success_count)

        if error_count > 0:
            message += "Erros: {}\n\n".format(error_count)
            message += "Detalhes:\n"
            for err in error_messages[:10]:  # Mostrar no máximo 10 erros
                message += "• {}\n".format(err)
            if len(error_messages) > 10:
                message += "... e mais {} erros".format(len(error_messages) - 10)

        print(message)  # Debug
        forms.alert(message, title="Resultado")


# ------------------------------------------------------------
# EXIBIR DIÁLOGO
# ------------------------------------------------------------
dlg = DuplicateDialog()
dlg.ShowDialog()