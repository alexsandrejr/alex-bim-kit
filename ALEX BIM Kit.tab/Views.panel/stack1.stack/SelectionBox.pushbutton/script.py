# -*- coding: utf-8 -*-
"""Auto Section Box - Cria vistas 3D com section box ajustado aos elementos selecionados"""

__title__ = 'Auto Section Box'
__author__ = 'André Rodrigues da Silva'
__doc__ = """
_____________________________________________________________________
Descrição:
Cria automaticamente vistas 3D com section box ajustado aos elementos 
selecionados. Funciona com elementos do modelo atual e de arquivos 
vinculados. Permite criar vistas temporárias ou permanentes com opções 
de margem customizável e alinhamento preciso aos elementos.
_____________________________________________________________________
"""

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import *
from pyrevit import revit, forms, script
import math

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument


def get_element_bounding_box(element, view=None):
    """Obtém o bounding box de um elemento, incluindo elementos de links"""
    try:
        if isinstance(element, RevitLinkInstance):
            # Para links, pegar o bounding box transformado
            link_doc = element.GetLinkDocument()
            if link_doc:
                transform = element.GetTotalTransform()
                link_bb = element.get_BoundingBox(view)
                if link_bb:
                    return link_bb

        bb = element.get_BoundingBox(view)
        return bb
    except:
        return None


def combine_bounding_boxes(bboxes):
    """Combina múltiplos bounding boxes em um único que engloba todos"""
    if not bboxes:
        return None

    min_x = min(bb.Min.X for bb in bboxes)
    min_y = min(bb.Min.Y for bb in bboxes)
    min_z = min(bb.Min.Z for bb in bboxes)

    max_x = max(bb.Max.X for bb in bboxes)
    max_y = max(bb.Max.Y for bb in bboxes)
    max_z = max(bb.Max.Z for bb in bboxes)

    combined_bb = BoundingBoxXYZ()
    combined_bb.Min = XYZ(min_x, min_y, min_z)
    combined_bb.Max = XYZ(max_x, max_y, max_z)

    return combined_bb


def expand_bounding_box(bb, margin_feet):
    """Expande o bounding box adicionando margem em todas as direções"""
    expanded_bb = BoundingBoxXYZ()
    expanded_bb.Min = XYZ(
        bb.Min.X - margin_feet,
        bb.Min.Y - margin_feet,
        bb.Min.Z - margin_feet
    )
    expanded_bb.Max = XYZ(
        bb.Max.X + margin_feet,
        bb.Max.Y + margin_feet,
        bb.Max.Z + margin_feet
    )
    return expanded_bb


def create_3d_view_with_section_box(name, section_box, template_view=None):
    """Cria uma nova vista 3D com section box definido"""

    # Obter ViewFamilyType para vista 3D
    view_family_types = FilteredElementCollector(doc) \
        .OfClass(ViewFamilyType) \
        .ToElements()

    view_3d_type = None
    for vft in view_family_types:
        if vft.ViewFamily == ViewFamily.ThreeDimensional:
            view_3d_type = vft
            break

    if not view_3d_type:
        raise Exception("Não foi possível encontrar ViewFamilyType para vista 3D")

    # Criar nova vista 3D
    new_view = View3D.CreateIsometric(doc, view_3d_type.Id)

    # Aplicar template se fornecido (ANTES de definir o nome)
    if template_view and isinstance(template_view, View3D):
        try:
            new_view.ViewTemplateId = template_view.Id
        except Exception as e:
            print("Erro ao aplicar template: {}".format(str(e)))

    # Definir nome único
    base_name = name
    attempt = 0
    while True:
        try:
            new_view.Name = name
            break
        except:
            attempt += 1
            name = "{}_{}".format(base_name, attempt)
            if attempt > 100:
                raise Exception("Não foi possível encontrar nome único para a vista")

    # Aplicar section box
    new_view.SetSectionBox(section_box)

    return new_view


def get_default_3d_view():
    """Retorna a vista 3D padrão ou a primeira disponível"""
    views_3d = FilteredElementCollector(doc) \
        .OfClass(View3D) \
        .ToElements()

    for view in views_3d:
        if not view.IsTemplate and "{3D}" in view.Name:
            return view

    for view in views_3d:
        if not view.IsTemplate:
            return view

    return None


class AutoSectionBoxDialog(forms.WPFWindow):
    def __init__(self):
        forms.WPFWindow.__init__(self, 'auto_section_box.xaml')

        # Configurações padrão
        self.margin_value.Text = "0.5"  # metros
        self.view_name.Text = "Section Box View"

        # Opções padrão
        self.create_new_view.IsChecked = True
        self.use_active_view.IsChecked = False
        self.include_links.IsChecked = True

        # Inicializar lista de templates
        self.view_templates_list = []

        # Preencher combo de templates
        self.populate_templates()

    def populate_templates(self):
        """Preenche o combo box com templates de vista 3D disponíveis"""
        try:
            # Coletar todos os templates de vista 3D
            view_templates = FilteredElementCollector(doc) \
                .OfClass(View) \
                .ToElements()

            # Filtrar apenas templates 3D
            templates_3d = []
            for vt in view_templates:
                if vt.IsTemplate and isinstance(vt, View3D):
                    templates_3d.append(vt)

            # Ordenar por nome
            templates_3d = sorted(templates_3d, key=lambda x: x.Name)

            # Guardar referência aos templates
            self.view_templates_list = templates_3d

            # Adicionar opção "Nenhum"
            self.template_combo.Items.Add("<Nenhum template>")

            # Adicionar templates ao combo
            for template in templates_3d:
                self.template_combo.Items.Add(template.Name)

            # Selecionar "Nenhum" por padrão
            self.template_combo.SelectedIndex = 0

        except Exception as e:
            print("Erro ao preencher templates: {}".format(str(e)))

    def get_selected_template(self):
        """Retorna o template selecionado ou None"""
        try:
            if self.template_combo.SelectedIndex <= 0:
                return None

            template_index = self.template_combo.SelectedIndex - 1
            if template_index < len(self.view_templates_list):
                return self.view_templates_list[template_index]

            return None
        except:
            return None

    def on_click_ok(self, sender, args):
        """Executar criação do section box"""
        try:
            self.process_section_box()
            self.DialogResult = True
            self.Close()
        except Exception as e:
            forms.alert("Erro ao criar section box:\n{}".format(str(e)), title="Erro")

    def on_click_cancel(self, sender, args):
        """Cancelar e fechar"""
        self.DialogResult = False
        self.Close()

    def process_section_box(self):
        """Processa a criação do section box"""

        # Obter seleção
        selection = [doc.GetElement(id) for id in uidoc.Selection.GetElementIds()]

        if not selection:
            forms.alert("Nenhum elemento selecionado!", title="Aviso")
            return

        # Obter margem em pés (converter de metros)
        try:
            margin_meters = float(self.margin_value.Text)
            margin_feet = margin_meters * 3.28084
        except:
            forms.alert("Valor de margem inválido!", title="Erro")
            return

        # Coletar bounding boxes
        bboxes = []
        default_view = get_default_3d_view()

        with forms.ProgressBar(title="Processando elementos...") as pb:
            for i, elem in enumerate(selection):
                pb.update_progress(i + 1, len(selection))

                bb = get_element_bounding_box(elem, default_view)
                if bb:
                    bboxes.append(bb)

                # Incluir elementos de links se solicitado
                if self.include_links.IsChecked and isinstance(elem, RevitLinkInstance):
                    link_doc = elem.GetLinkDocument()
                    if link_doc:
                        transform = elem.GetTotalTransform()
                        # Processar elementos do link (simplificado)
                        link_elements = FilteredElementCollector(link_doc) \
                            .WhereElementIsNotElementType() \
                            .ToElements()

                        for link_elem in link_elements[:100]:  # Limitar para performance
                            link_bb = link_elem.get_BoundingBox(None)
                            if link_bb:
                                # Transformar bounding box do link
                                transformed_bb = BoundingBoxXYZ()
                                transformed_bb.Min = transform.OfPoint(link_bb.Min)
                                transformed_bb.Max = transform.OfPoint(link_bb.Max)
                                bboxes.append(transformed_bb)

        if not bboxes:
            forms.alert("Não foi possível obter bounding box dos elementos!", title="Erro")
            return

        # Combinar todos os bounding boxes
        combined_bb = combine_bounding_boxes(bboxes)

        # Expandir com margem
        final_bb = expand_bounding_box(combined_bb, margin_feet)

        # Iniciar transação
        t = Transaction(doc, "Auto Section Box")
        t.Start()

        try:
            if self.create_new_view.IsChecked:
                # Criar nova vista 3D
                view_name = self.view_name.Text.strip()
                if not view_name:
                    view_name = "Section Box View"

                new_view = create_3d_view_with_section_box(
                    view_name,
                    final_bb,
                    self.get_selected_template()
                )

                t.Commit()

                # Abrir a nova vista
                uidoc.ActiveView = new_view
                uidoc.RefreshActiveView()

                forms.alert(
                    "Vista 3D '{}' criada com sucesso!".format(new_view.Name),
                    title="Sucesso"
                )

            else:
                # Aplicar na vista ativa
                active_view = uidoc.ActiveView

                if not isinstance(active_view, View3D):
                    raise Exception("A vista ativa não é uma vista 3D!")

                active_view.SetSectionBox(final_bb)

                t.Commit()

                uidoc.RefreshActiveView()

                forms.alert(
                    "Section box aplicado à vista ativa!",
                    title="Sucesso"
                )

        except Exception as e:
            t.RollBack()
            raise


# Verificar se há elementos selecionados
selection = [doc.GetElement(id) for id in uidoc.Selection.GetElementIds()]

if not selection:
    forms.alert(
        "Nenhum elemento selecionado!\n\nSelecione elementos e execute o comando novamente.",
        title="Aviso"
    )
else:
    # Exibir diálogo
    try:
        dlg = AutoSectionBoxDialog()
        dlg.ShowDialog()
    except Exception as e:
        forms.alert("Erro ao abrir diálogo:\n{}".format(str(e)), title="Erro")