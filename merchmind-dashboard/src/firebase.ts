import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider, signInWithPopup, signOut, onAuthStateChanged, type User } from 'firebase/auth';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || '',
  authDomain: 'merchmind-cb1f9.firebaseapp.com',
  projectId: 'merchmind-cb1f9',
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

const provider = new GoogleAuthProvider();

const ALLOWED_EMAILS = [
  'webgenerations77@gmail.com',
  'spinachthecow@gmail.com',
];

export function isAllowedUser(user: User | null): boolean {
  return !!user?.email && ALLOWED_EMAILS.includes(user.email);
}

export async function signInWithGoogle(): Promise<User> {
  const result = await signInWithPopup(auth, provider);
  if (!isAllowedUser(result.user)) {
    await signOut(auth);
    throw new Error('Access denied. Your email is not authorized.');
  }
  return result.user;
}

export async function logout(): Promise<void> {
  await signOut(auth);
}

export { onAuthStateChanged, type User };
