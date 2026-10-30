# -*- coding: utf-8 -*-

from pyrevit import revit, DB, forms, script

doc    = revit.doc
view   = doc.ActiveView
output = script.get_output()


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():

    conduits = (
        DB.FilteredElementCollector(doc)
        .OfCategory(DB.BuiltInCategory.OST_Conduit)
        .WhereElementIsNotElementType()
        .ToElements()
    )

    if not conduits:
        forms.alert("Nenhum eletroduto encontrado.", exitscript=True)

    options = DB.Options()
    options.View = view

    painted = 0
    errors  = 0

    with revit.Transaction("Aplicar Material REAL (Paint) nos Eletrodutos"):

        for conduit in conduits:

            conduit_type = doc.GetElement(conduit.GetTypeId())
            if conduit_type is None:
                continue

            # pegar material do tipo (IGUAL seu caso)
            param = conduit_type.LookupParameter("Material")

            if param is None or not param.HasValue:
                errors += 1
                continue

            mat_id = param.AsElementId()

            if mat_id == DB.ElementId.InvalidElementId:
                errors += 1
                continue

            # 🔥 PEGAR GEOMETRIA
            geo = conduit.get_Geometry(options)

            if geo is None:
                continue

            for g in geo:

                # só sólidos
                if not isinstance(g, DB.Solid):
                    continue

                if g.Faces.IsEmpty:
                    continue

                # 🔥 PINTAR TODAS AS FACES
                for face in g.Faces:
                    try:
                        doc.Paint(conduit.Id, face, mat_id)
                        painted += 1
                    except:
                        pass

    output.print_md("## Resultado")
    output.print_md("Faces pintadas: {}".format(painted))
    output.print_md("Erros: {}".format(errors))


# ---------------------------------------------------------------------------
# RUN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()