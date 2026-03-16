import { createRouter, createWebHistory } from 'vue-router'

import DefaultLayout from '../layouts/DefaultLayout.vue'
import PdfToPptPage from '../pages/PdfToPptPage.vue'
import PdfToImagesPage from '../pages/PdfToImagesPage.vue'
import ImagesToPdfPage from '../pages/ImagesToPdfPage.vue'
import InpaintPage from '../pages/InpaintPage.vue'
import OcrPage from '../pages/OcrPage.vue'

const routes = [
  {
    path: '/',
    component: DefaultLayout,
    children: [
      {
        path: '',
        name: 'PdfToPpt',
        component: PdfToPptPage,
      },
      {
        path: 'pdf-to-images',
        name: 'PdfToImages',
        component: PdfToImagesPage,
      },
      {
        path: 'images-to-pdf',
        name: 'ImagesToPdf',
        component: ImagesToPdfPage,
      },
      {
        path: 'ocr',
        name: 'Ocr',
        component: OcrPage,
      },
      {
        path: 'inpaint',
        name: 'Inpaint',
        component: InpaintPage,
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
