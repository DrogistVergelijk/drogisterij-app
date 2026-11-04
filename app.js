javascript
// Hier koppelen we straks jouw specifieke Google Sheet link aan
const SHEET_URL = 'https://docs.google.com/spreadsheets/d/1yXY2u4nidJi7lQcjUciqxc--aHMs24BlrWdp-_0VJI0/edit?usp=sharing';


async function laadEchteProducten() {
    const container = document.getElementById('products-container');
    container.innerHTML = "<p style='text-align:center;'>Producten live laden uit database...</p>";
    
    try {
        const response = await fetch(SHEET_URL);
        const csvTekst = await response.text();
        
        // We splitsen de tekst netjes op per rij
        const rijen = csvTekst.split('\n').slice(1); 
        container.innerHTML = ""; // Wis het laad-tekstje
        
        rijen.forEach(rij => {
            // We halen de aanhalingstekens weg die Google Sheets meestuurt
            const kolommen = rij.split('","').map(item => item.replace(/"/g, '').trim());
            
            // Volgorde check: A=ID, B=Naam, C=Link, D=ActieAantal, E=ActiePrijs, F=Prijs
            const id = kolommen[0];
            const naam = kolommen[1];
            const link = kolommen[2];
            const actieAantal = kolommen[3];
            const actiePrijs = kolommen[4];
            const prijs = kolommen[5];
            
            if (naam) { // Alleen tonen als de rij niet leeg is
                let actieBadge = "";
                // Als er een actie-aantal is ingevuld (bijv 3 voor 11), toon de knaller-badge!
                if (actieAantal && actiePrijs) {
                    actieBadge = `<div class="badge">🔥 ACTIE: ${actieAantal} voor €${actiePrijs}</div>`;
                }

                container.innerHTML += `
                    <div class="product-card">
                        <div class="title">${naam}</div>
                        <div class="price">Stukprijs: ${prijs}</div>
                        ${actieBadge}
                        <a href="${link}" target="_blank" class="btn">Bekijk bij Drogisterij</a>
                    </div>
                `;
            }
        });
    } catch (fout) {
        container.innerHTML = "<p style='color:red;'>Fout bij laden van live data.</p>";
        console.error(fout);
    }
}

laadEchteProducten();
