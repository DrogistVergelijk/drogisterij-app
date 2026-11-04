javascript
// Hier koppelen we straks jouw specifieke Google Sheet link aan
const SHEET_URL = 'HIER_KOMT_STRAKS_JE_LINK';


// Een test-functie om te laten zien hoe de app je data opbouwt
function toonProducten() {
    const container = document.getElementById('products-container');
    
    // Dit is een voorbeeld van hoe de app straks jouw kolommen uitleest:
    const voorbeeldProduct = {
        naam: "Kruidvat Magnesium Slapen & Rust",
        prijs: "€6.29",
        actieAantal: "3",
        actiePrijs: "11",
        link: "#"
    };


    container.innerHTML = `
        <div class="product-card">
            <div class="title">${voorbeeldProduct.naam}</div>
            <div class="price">Normaal: ${voorbeeldProduct.prijs}</div>
            <div class="badge"> ACTIE: ${voorbeeldProduct.actieAantal} voor €${voorbeeldProduct.actiePrijs}</div>
            <a href="${voorbeeldProduct.link}" class="btn">Voeg toe aan mandje</a>
        </div>
    `;
}


toonProducten();