from pathlib import Path
from unittest.mock import MagicMock, patch
import json
import pytest
from scripts.extract_brazinst import parse_verbete_html, BrazinstExtractor

SAMPLE_VERBETE_HTML = '''
<!DOCTYPE html>
<html>
<head><title>Agogô — LABEET</title></head>
<body>
<div id="content">
    <h1 class="documentFirstHeading">Agogô</h1>
    <div class="documentByLine">
        por <span class="documentAuthor">danielrocha</span> —
        <span class="documentPublished">publicado 28/03/2018 10h40</span>,
        <span class="documentModified">última modificação 26/01/2026 16h37</span>
    </div>
    <div id="content-core">
        <div id="parent-fieldname-text">
            <p><img src="http://150.165.254.38/labeet/agogo.jpg" alt="Agogô"></p>
            <p>O agogô foi levado pelos escravos africanos para as Américas...</p>
            <h3>Referências</h3>
            <p>C. A. Moloney: ‘On the Melodies...’ (1889)</p>
            <h3>Fonografia</h3>
            <p><a href="https://www.youtube.com/watch?v=_kQIk1jJb9c">Exemplo 1</a></p>
            <p><i>Alice L. Satomi</i></p>
        </div>
    </div>
</div>
</body></html>
'''


def test_parse_verbete_html():
    data = parse_verbete_html(
        SAMPLE_VERBETE_HTML,
        "http://150.165.254.38/labeet/contents/paginas/acervo-brazinst/copy_of_idiofones/agogo"
    )
    assert data["title"] == "Agogô"
    assert data["slug"] == "agogo"
    assert data["family"] == "idiofones"
    assert data["published_date"] == "2018-03-28"
    assert data["modified_date"] == "2026-01-26"
    assert "Alice L. Satomi" in data["body"]
    assert "### Referências" in data["body"]
    assert len(data["audio_video_links"]) == 1
    assert data["audio_video_links"][0]["url"] == "https://www.youtube.com/watch?v=_kQIk1jJb9c"
    assert data["audio_video_links"][0]["title"] == "Exemplo 1"
    assert len(data["image_urls"]) >= 1
    assert data["image_urls"][0] == "http://150.165.254.38/labeet/agogo.jpg"


SAMPLE_PLONE_NITF_HTML = '''
<!DOCTYPE html>
<html>
<head><title>Afofiê — LABEET</title></head>
<body>
<div id="content">
    <article prefix="rnews: http://iptc.org/std/rNews/2011-10-07#" typeof="Article">
        <h1 class="documentFirstHeading">Afofiê</h1>
        <h2 class="nitfSubtitle">Flauta tradicional</h2>
        <div class="documentDescription">Pequena flauta de taquara com bocal de madeira.</div>
        <div class="documentByLine" id="plone-document-byline">
            <span class="documentPublished">publicado: <span>17/08/2017 13h11</span></span>
            <span class="documentModified">última modificação: <span>11/03/2026 12h19</span></span>
        </div>
        <div class="newsLeftPane">
            <div class="newsImageContainer">
                <a class="parent-nitf-image" href="Afofie/@@slideshow_view">
                    <img src="Afofie.jpg/@@images/thumb.jpeg" alt="Foto Afofiê" />
                </a>
            </div>
        </div>
        <div property="rnews:articleBody">
            <p>Aerofone (4) de sopro (4.2.), da família das flautas.</p>
            <p style="text-align: right;">Gabriel Felipe Sena & Alice S. Lumi.</p>
            <h3>Referências</h3>
            <p>CASCUDO, Câmara. Dicionário do Folclore Brasileiro.</p>
            <p>DE ANDRADE, Mário. Dicionário Musical Brasileiro.</p>
        </div>
    </article>
</div>
</body></html>
'''


def test_parse_verbete_html_plone_nitf():
    data = parse_verbete_html(
        SAMPLE_PLONE_NITF_HTML,
        "http://150.165.254.38/labeet/contents/paginas/acervo-brazinst/copy_of_aerofones/Afofie"
    )
    assert data["title"] == "Afofiê"
    assert data["slug"] == "afofie"
    assert data["family"] == "aerofones"
    assert data["subtitle"] == "Flauta tradicional"
    assert "Pequena flauta de taquara" in data["description"]
    assert data["published_date"] == "2017-08-17"
    assert data["modified_date"] == "2026-03-11"
    assert "Aerofone (4) de sopro" in data["body"]
    assert "CASCUDO" in data["body"]
    assert len(data["image_urls"]) >= 1


def test_brazinst_extractor_run(tmp_path: Path):
    output_dir = tmp_path / "content_brazinst"
    extractor = BrazinstExtractor(output_dir)

    category_html = '''
    <html><body>
        <div id="content">
            <a class="summary" href="http://150.165.254.38/labeet/contents/paginas/acervo-brazinst/copy_of_idiofones/agogo">Agogô</a>
            <a class="summary" href="http://150.165.254.38/labeet/contents/paginas/acervo-brazinst/copy_of_idiofones/tabela-organologica">Tabela</a>
        </div>
    </body></html>
    '''

    def mock_fetch(url, session, **kwargs):
        resp = MagicMock()
        if "copy_of_idiofones/agogo" in url:
            resp.status_code = 200
            resp.text = SAMPLE_VERBETE_HTML
            resp.content = SAMPLE_VERBETE_HTML.encode("utf-8")
        elif "agogo.jpg" in url:
            resp.status_code = 200
            resp.content = b"fake-jpeg-image-data"
        elif "copy_of_idiofones" in url:
            resp.status_code = 200
            resp.text = category_html
            resp.content = category_html.encode("utf-8")
        else:
            # Other categories empty / 404
            resp.status_code = 404
            resp.text = ""
            resp.content = b""
        return resp

    with patch("scripts.extract_brazinst.fetch_url", side_effect=mock_fetch):
        extractor.run()

    # Verify markdown generated
    md_file = output_dir / "instruments" / "idiofones" / "agogo.md"
    assert md_file.exists()
    content = md_file.read_text(encoding="utf-8")
    assert "title: Agogô" in content
    assert "family: idiofones" in content
    assert "file: media/idiofones/agogo/img_01.jpg" in content

    # Verify image saved
    img_file = output_dir / "media" / "idiofones" / "agogo" / "img_01.jpg"
    assert img_file.exists()
    assert img_file.read_bytes() == b"fake-jpeg-image-data"

    # Verify catalog JSON
    catalog_file = output_dir / "brazinst_catalog.json"
    assert catalog_file.exists()
    cat_data = json.loads(catalog_file.read_text(encoding="utf-8"))
    assert cat_data["total_instruments"] == 1
    assert cat_data["instruments"][0]["id"] == "agogo"
    assert cat_data["instruments"][0]["media_count"] == 1

    # Verify resume behavior
    with patch("scripts.extract_brazinst.fetch_url", side_effect=mock_fetch) as mock_f:
        extractor2 = BrazinstExtractor(output_dir)
        extractor2.run()
        # The instrument verbete should not be fetched again
        called_urls = [call.args[0] for call in mock_f.call_args_list]
        assert not any("agogo" in u and "jpg" not in u for u in called_urls if "copy_of_idiofones/agogo" == u)
