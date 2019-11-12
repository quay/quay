import { ViewArrayImpl } from "static/js/services/view-array/view-array.impl";


/**
 * Specialized wrapper around array which provides a toggle() method for viewing the contents of the
 * array in a manner that is asynchronously filled in over a short time period. This prevents long
 * pauses in the UI for ngRepeat's when the array is significant in size.
 */
export abstract class ViewArray {

    /**
     * The stored entries.
     */
    public abstract entries: any;

    /**
     * If the entries are displayed.
     */
    public abstract isVisible: boolean;

    /**
     * The displayed entries.
     */
    public abstract visibleEntries: any[];

    /**
     * If there are stored entries.
     */
    public abstract hasEntries: boolean;

    /**
     * If there are entries not visible.
     */
    public abstract hasHiddenEntries: boolean;

    /**
     * Get the number of entries stored.
     * @return number The number of entries.
     */
    public abstract length(): number;

    /**
     * Get a specific entry.
     * @param index The index of the entry.
     * @return element The element at the given index.
     */
    public abstract get(index: number): any;

    /**
     * Add a new element.
     * @param elem The new element.
     */
    public abstract push(elem: any): void;

    /**
     * Toggle whether the elements are visible.
     */
    public abstract toggle(): void;

    /**
     * Set whether the elements are visible.
     * @param newState True/False if the contents are visible.
     */
    public abstract setVisible(newState: boolean): void;

    /**
     * Factory function to create a new ViewArray.
     * @return viewArray New ViewArray instance.
     */
    public abstract create(): ViewArrayImpl;
}
