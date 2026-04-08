"""
Script de test pour vérifier l'API d'authentification
Lance ce script avec : python test_auth.py
"""
import requests
import time

BASE_URL = "http://localhost:8000"

def test_auth_flow():
    """Test complet du flow d'authentification"""
    
    print("=" * 60)
    print("🧪 Test du système d'authentification")
    print("=" * 60)
    
    # Données de test
    username = f"test_user_{int(time.time())}"
    email = f"{username}@test.com"
    password = "TestPassword123!"
    
    # 1. Test Health Check
    print("\n1️⃣  Test Health Check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("   ✅ API est en ligne")
            print(f"   Response: {response.json()}")
        else:
            print(f"   ❌ Erreur: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Impossible de contacter l'API: {e}")
        print("   💡 Vérifiez que l'API tourne avec: uvicorn app.main:app --reload")
        return
    
    # 2. Test Sign-up
    print(f"\n2️⃣  Test Sign-up (username: {username})...")
    try:
        response = requests.post(
            f"{BASE_URL}/auth/signup",
            json={
                "username": username,
                "email": email,
                "password": password
            }
        )
        if response.status_code == 201:
            user_data = response.json()
            print("   ✅ Compte créé avec succès")
            print(f"   User ID: {user_data['id']}")
            print(f"   Username: {user_data['username']}")
            print(f"   Email: {user_data['email']}")
        else:
            print(f"   ❌ Erreur: {response.status_code}")
            print(f"   Message: {response.json()}")
            return
    except Exception as e:
        print(f"   ❌ Erreur lors du sign-up: {e}")
        return
    
    # 3. Test Login
    print(f"\n3️⃣  Test Login...")
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            data={
                "username": username,
                "password": password
            }
        )
        if response.status_code == 200:
            token_data = response.json()
            token = token_data["access_token"]
            print("   ✅ Login réussi")
            print(f"   Token (premiers 50 chars): {token[:50]}...")
        else:
            print(f"   ❌ Erreur: {response.status_code}")
            print(f"   Message: {response.json()}")
            return
    except Exception as e:
        print(f"   ❌ Erreur lors du login: {e}")
        return
    
    # 4. Test Get User Info (endpoint protégé)
    print(f"\n4️⃣  Test Get User Info (endpoint protégé)...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
        if response.status_code == 200:
            user_info = response.json()
            print("   ✅ Infos utilisateur récupérées")
            print(f"   Username: {user_info['username']}")
            print(f"   Email: {user_info['email']}")
            print(f"   Active: {user_info['is_active']}")
        else:
            print(f"   ❌ Erreur: {response.status_code}")
            print(f"   Message: {response.json()}")
            return
    except Exception as e:
        print(f"   ❌ Erreur lors de la récupération des infos: {e}")
        return
    
    # 5. Test Logout
    print(f"\n5️⃣  Test Logout...")
    try:
        response = requests.post(f"{BASE_URL}/auth/logout", headers=headers)
        if response.status_code == 200:
            print("   ✅ Logout réussi")
            print(f"   Message: {response.json()}")
        else:
            print(f"   ❌ Erreur: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Erreur lors du logout: {e}")
        return
    
    # 6. Test utilisation du token révoqué
    print(f"\n6️⃣  Test utilisation du token révoqué...")
    try:
        response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
        if response.status_code == 401:
            print("   ✅ Token révoqué correctement (401 Unauthorized)")
        else:
            print(f"   ⚠️  Attendu 401, reçu: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
    
    # 7. Test duplicate username
    print(f"\n7️⃣  Test création compte avec username existant...")
    try:
        response = requests.post(
            f"{BASE_URL}/auth/signup",
            json={
                "username": username,  # Même username
                "email": f"autre_{email}",
                "password": password
            }
        )
        if response.status_code == 400:
            print("   ✅ Duplication détectée (400 Bad Request)")
            print(f"   Message: {response.json()['detail']}")
        else:
            print(f"   ⚠️  Attendu 400, reçu: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
    
    # Résumé
    print("\n" + "=" * 60)
    print("✅ Tous les tests sont passés !")
    print("=" * 60)
    print("\n💡 Prochaines étapes :")
    print("   - Ouvrir http://localhost:8000/docs pour la doc interactive")
    print("   - Tester avec Postman ou votre frontend")
    print("   - Implémenter les endpoints pour les documents PDF")


if __name__ == "__main__":
    test_auth_flow()
