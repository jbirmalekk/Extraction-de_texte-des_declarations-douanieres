from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

# Importer TON get_db existant
from app.database import get_db

from app.models.document import Document, Taxe, Article
from app.models.schemas import (OCRResultSchema, OCRValidationSchema,
                                 DocumentResponseSchema)
from app.services.pipeline import process_document

router = APIRouter(prefix="/api", tags=["OCR"])


@router.post("/ocr")
async def extract_declaration(
    file       : UploadFile = File(...),
    fast_mode  : bool = False,
    use_deskew : bool = True,
    db         : Session = Depends(get_db),   # ← ton get_db
):
    allowed = {"image/jpeg","image/png","image/tiff",
               "application/pdf","image/jpg"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400,
                            detail="Format non supporte (JPG, PNG, TIFF, PDF)")

    file_bytes = await file.read()

    result = process_document(
        file_bytes = file_bytes,
        filename   = file.filename,
        fast_mode  = fast_mode,
        use_deskew = use_deskew,
    )

    if "erreur" in result:
        detail = (
            f"{result['erreur']} | fichier={file.filename} | type={file.content_type}"
        )
        raise HTTPException(status_code=422, detail=detail)

    # Sauvegarder en base
    doc = Document(
        fichier                  = result.get("fichier"),
        statut                   = "ocr_extrait",
        numero_declaration       = result.get("numero_declaration"),
        date_declaration         = result.get("date_declaration"),
        type_declaration         = result.get("type_declaration"),
        nbre_articles            = result.get("nbre_articles"),
        exportateur_nom          = result.get("exportateur_nom"),
        exportateur_code         = result.get("exportateur_code"),
        importateur_nom          = result.get("importateur_nom"),
        importateur_pays         = result.get("importateur_pays"),
        declarant_code           = result.get("declarant_code"),
        declarant_nom            = result.get("declarant_nom"),
        mode_transport           = result.get("mode_transport"),
        date_arrivee_depart      = result.get("date_arrivee_depart"),
        pays_provenance          = result.get("pays_provenance"),
        pays_destination         = result.get("pays_destination"),
        adresse_entreposage      = result.get("adresse_entreposage"),
        mode_livraison           = result.get("mode_livraison"),
        devise                   = result.get("devise"),
        montant_ptfn             = result.get("montant_ptfn"),
        valeur_fob_dt            = result.get("valeur_fob_dt"),
        taux_conversion          = result.get("taux_conversion"),
        designation_marchandises = result.get("designation_marchandises"),
        poids_brut               = result.get("poids_brut"),
        poids_net                = result.get("poids_net"),
        bureau_douane            = result.get("bureau_douane"),
        code_gdt                 = result.get("code_gdt"),
        montant_liquidation      = result.get("montant_liquidation"),
        itineraire               = result.get("itineraire"),
        num_agrement             = result.get("num_agrement"),
        num_repertoire           = result.get("num_repertoire"),
        cle_authentification     = result.get("cle_authentification"),
        score_confiance          = result.get("score_confiance"),
        qualite                  = result.get("qualite"),
        flags_validation         = result.get("flags_validation", []),
        texte_brut               = result.get("texte_brut","")[:5000],
    )
    db.add(doc)
    db.flush()

    for t in result.get("taxes", []):
        db.add(Taxe(
            document_id = doc.id,
            code        = t.get("code"),
            assiette    = t.get("assiette"),
            quotite     = t.get("quotite"),
            montant     = t.get("montant"),
        ))

    for a in result.get("articles", []):
        db.add(Article(
            document_id   = doc.id,
            num_ligne     = a.get("num_ligne"),
            code_hs       = a.get("code_hs"),
            designation   = a.get("designation"),
            quantite      = a.get("quantite"),
            unite         = a.get("unite"),
            prix_unitaire = a.get("prix_unitaire"),
            total_ligne   = a.get("total_ligne"),
        ))

    db.commit()
    db.refresh(doc)

    result["id"] = doc.id
    return JSONResponse(content=result)


@router.put("/ocr/{document_id}/valider")
async def valider_declaration(
    document_id : int,
    data        : OCRValidationSchema,
    db          : Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouve")

    champs = [
        "numero_declaration","date_declaration","type_declaration",
        "exportateur_nom","importateur_nom","importateur_pays",
        "mode_transport","devise","montant_ptfn","valeur_fob_dt",
        "bureau_douane","montant_liquidation",
    ]
    for ch in champs:
        val = getattr(data, ch, None)
        if val is not None:
            setattr(doc, ch, val)

    doc.statut = data.statut or "valide"
    db.commit()

    return {"message": "Document valide", "id": doc.id, "statut": doc.statut}


@router.get("/documents", response_model=list[DocumentResponseSchema])
async def liste_documents(
    skip  : int = 0,
    limit : int = 50,
    db    : Session = Depends(get_db),
):
    return db.query(Document).order_by(
        Document.created_at.desc()
    ).offset(skip).limit(limit).all()


@router.get("/documents/{document_id}")
async def get_document(
    document_id : int,
    db          : Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouve")
    return doc