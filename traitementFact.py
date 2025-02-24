import asyncio
import aiohttp

async def process_invoice(session, invoice_file):
    async with session.post("http://localhost:8000/upload_invoice/", files={"file": invoice_file}) as response:
        return await response.json()

async def process_invoices(files):
    async with aiohttp.ClientSession() as session:
        tasks = [process_invoice(session, file) for file in files]
        results = await asyncio.gather(*tasks)
        return results

# Liste des fichiers de factures à traiter
files = ["Template1_Instance25.png", "Template1_Instance78.png", "Template1_Instance22.png", ...]

# Lancer le traitement parallèle
results = asyncio.run(process_invoices(files))
