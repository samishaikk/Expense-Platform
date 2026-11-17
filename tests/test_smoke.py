from tests.factories import TEST_PASSWORD

def test_health(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_login_returns_token(client, employee):
    response = client.post(
        '/auth/login',
        data={'username': employee.email, 'password': TEST_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['token_type'] == 'bearer'
    assert body['access_token']