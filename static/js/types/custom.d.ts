declare var System: {
  import: (module: string) => Promise<any>;
};

declare module "*.html" {
  const value: string;
  export = value;
}

declare module "*.css" {
  const value: string;
  export = value;
}
