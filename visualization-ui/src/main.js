import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

// Import styles
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import './style.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)

console.log('Mounting Vue app...')
app.mount('#app')
console.log('Vue app mounted')