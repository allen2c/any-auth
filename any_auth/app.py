import fastapi
import fastapi.security

app = fastapi.FastAPI()

oauth2_scheme = fastapi.security.OAuth2PasswordBearer(tokenUrl="token")
