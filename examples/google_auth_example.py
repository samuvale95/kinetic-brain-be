#!/usr/bin/env python3
"""
Esempio di utilizzo dell'autenticazione Google OAuth
"""

import httpx
import asyncio
from typing import Dict, Any


class GoogleAuthExample:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def get_google_auth_url(self) -> str:
        """Ottiene l'URL di autorizzazione Google"""
        response = await self.client.get(f"{self.base_url}/auth/google/url")
        response.raise_for_status()
        data = response.json()
        return data["auth_url"]
    
    async def authenticate_with_google(self, code: str, redirect_uri: str = None) -> Dict[str, Any]:
        """Autentica l'utente con Google OAuth"""
        payload = {
            "code": code,
            "redirect_uri": redirect_uri
        }
        
        response = await self.client.post(
            f"{self.base_url}/auth/google/login",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Ottiene le informazioni dell'utente corrente"""
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await self.client.get(
            f"{self.base_url}/auth/me",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    async def test_protected_endpoint(self, access_token: str) -> Dict[str, Any]:
        """Testa un endpoint protetto"""
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await self.client.get(
            f"{self.base_url}/dashboard/stats",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Chiude il client HTTP"""
        await self.client.aclose()


async def main():
    """Esempio di utilizzo"""
    auth_example = GoogleAuthExample()
    
    try:
        # 1. Ottieni l'URL di autorizzazione Google
        print("1. Ottenendo URL di autorizzazione Google...")
        auth_url = await auth_example.get_google_auth_url()
        print(f"URL di autorizzazione: {auth_url}")
        print("\nVai a questo URL nel browser per autorizzare l'applicazione")
        print("Dopo l'autorizzazione, copia il codice dalla URL di callback")
        
        # 2. Simula l'autenticazione (in un'app reale, il codice verrebbe dal frontend)
        print("\n2. Inserisci il codice di autorizzazione:")
        code = input("Codice: ").strip()
        
        if code:
            print("Autenticando con Google...")
            tokens = await auth_example.authenticate_with_google(code)
            print(f"Token ricevuti: {tokens}")
            
            access_token = tokens["access_token"]
            
            # 3. Ottieni le informazioni dell'utente
            print("\n3. Ottenendo informazioni utente...")
            user_info = await auth_example.get_user_info(access_token)
            print(f"Informazioni utente: {user_info}")
            
            # 4. Testa un endpoint protetto
            print("\n4. Testando endpoint protetto...")
            stats = await auth_example.test_protected_endpoint(access_token)
            print(f"Statistiche dashboard: {stats}")
            
        else:
            print("Nessun codice fornito, esempio terminato")
    
    except Exception as e:
        print(f"Errore: {e}")
    
    finally:
        await auth_example.close()


if __name__ == "__main__":
    asyncio.run(main())
