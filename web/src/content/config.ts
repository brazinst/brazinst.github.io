import { defineCollection, z } from 'astro:content';

const instruments = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string().min(1),
    slug: z.string().optional(),
    family: z.enum(['aerofones', 'cordofones', 'idiofones', 'membranofones']),
    mimo_code: z.string().nullable().optional(),
    source_url: z.string().url().nullable().optional(),
    author: z.string().nullable().optional(),
    reviewer: z.string().nullable().optional(),
    published_date: z.string().nullable().optional(),
    modified_date: z.string().nullable().optional(),
    thumbnail: z.string().nullable().optional(),
    images: z.array(z.object({
      file: z.string(),
      original_url: z.string().optional(),
      caption: z.string().optional(),
      rights: z.string().optional(),
    })).default([]),
    audio_video_links: z.array(z.object({
      title: z.string(),
      url: z.string(),
      access_date: z.string().optional(),
    })).default([]),
    references: z.array(z.string()).default([]),
  }),
});

export const collections = { instruments };
