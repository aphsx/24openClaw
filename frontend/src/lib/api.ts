import axios from 'axios';
import { io } from 'socket.io-client';
import { twMerge } from 'tailwind-merge';
import { clsx, type ClassValue } from 'clsx';

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001';

export const socket = io(API_URL);

const api = axios.create({
    baseURL: `${API_URL}/api`,
});

export const fetchPairs = async () => {
    const { data } = await api.get('/pairs');
    return data;
};

export const triggerScan = async () => {
    const { data } = await api.post('/scan/trigger');
    return data;
};

export const fetchPositions = async () => {
    const { data } = await api.get('/positions');
    return data;
};


export const fetchConfig = async () => {
    const { data } = await api.get('/config');
    return data;
};

export const updateConfig = async (key: string, value: number) => {
    const { data } = await api.put(`/config/${key}`, { value });
    return data;
};
