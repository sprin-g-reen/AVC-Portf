import type { Schema, Struct } from '@strapi/strapi';

export interface ServiceItemCommon extends Struct.ComponentSchema {
  collectionName: 'components_service_item_commons';
  info: {
    displayName: 'common';
  };
  attributes: {
    description: Schema.Attribute.Text;
    image: Schema.Attribute.Media<'images' | 'files' | 'videos' | 'audios'>;
    title: Schema.Attribute.String;
  };
}

export interface TextColor extends Struct.ComponentSchema {
  collectionName: 'components_text_colors';
  info: {
    displayName: 'color';
  };
  attributes: {
    hex_code: Schema.Attribute.String;
    name: Schema.Attribute.String;
  };
}

export interface TextImageItem extends Struct.ComponentSchema {
  collectionName: 'components_text_image_items';
  info: {
    displayName: 'image_item';
  };
  attributes: {
    color: Schema.Attribute.String;
    image: Schema.Attribute.Media<'images' | 'files' | 'videos' | 'audios'>;
    image_alt: Schema.Attribute.String;
    Sizes: Schema.Attribute.JSON;
  };
}

declare module '@strapi/strapi' {
  export module Public {
    export interface ComponentSchemas {
      'service-item.common': ServiceItemCommon;
      'text.color': TextColor;
      'text.image-item': TextImageItem;
    }
  }
}
