import axios from 'axios';
import { io } from 'socket.io-client';

export const socket = io('http://localhost:3001');

const api = axios.create({
    baseURL: 'http://localhost:3001/api',
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

export const fetchTrades = async () => {
    const { data } = await api.get('/trades');
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
